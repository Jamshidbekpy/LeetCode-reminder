from __future__ import annotations

import asyncio
import re
import pytz
from redis import Redis
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import get_settings
from app.storage import Storage
from app.database import Database
from app.scheduler import run_scheduler
from app.leetcode import solved_today, problem_link

HHMM_RE = re.compile(r"^\d{2}:\d{2}$")

def _valid_hhmm(t: str) -> bool:
    if not HHMM_RE.match(t):
        return False
    hh, mm = t.split(":")
    h, m = int(hh), int(mm)
    return 0 <= h <= 23 and 0 <= m <= 59

def _normalize_username(u: str) -> str:
    return u.strip().lstrip("@")

# ---------- Commands ----------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id
    
    # Get user info from Telegram
    user = update.effective_user
    telegram_username = user.username if user else None
    telegram_first_name = user.first_name if user else None
    telegram_last_name = user.last_name if user else None
    
    storage.add_user(
        chat_id=chat_id,
        telegram_username=telegram_username,
        telegram_first_name=telegram_first_name,
        telegram_last_name=telegram_last_name,
    )

    await update.message.reply_text(
        "🤖 LeetCode Reminder botga xush kelibsiz!\n\n"
        "1) Username bog‘lash:\n"
        "   /setusername your_leetcode_username\n\n"
        "2) Reminder vaqtlarini ko‘rish:\n"
        "   /listremind\n\n"
        "Yordam: /help"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Komandalar:\n"
        "/start - botni ulash\n"
        "/stop - botni o‘chirish (shu chat uchun)\n"
        "/setusername <username> - LeetCode username bog‘lash\n"
        "/username - ulangan username ni ko‘rish\n"
        "/check - hozir tekshir (Accepted bormi)\n"
        "/status - bugungi holat\n"
        "/listremind - reminder vaqtlarini ko‘rish\n"
        "/setremind 20:00 - reminder vaqtini bitta qilib qo‘yish\n"
        "/addremind 09:00 - reminder vaqt qo‘shish\n"
        "/delremind 09:00 - reminder vaqt o‘chirish\n"
        "/timezone Asia/Tashkent - timezone o‘zgartirish\n"
        "/tz - hozirgi timezone\n"
    )

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id
    storage.remove_user(chat_id)
    await update.message.reply_text("🛑 O‘chirildi. Endi bu chatga eslatmalar kelmaydi.")

async def setusername_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.application.bot_data["settings"]
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("Misol: /setusername jamshidbek")
        return

    username = _normalize_username(context.args[0])
    tz = storage.get_timezone(chat_id, settings.default_tz)

    # External API orqali username ni oldindan tekshiramiz.
    # Tekshiruvdan o'tmagan username saqlanmaydi.
    try:
        solved_today(username, tz, max_retries=2)
    except RuntimeError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            await update.message.reply_text(
                f"❌ LeetCode foydalanuvchi topilmadi: {username}\n"
                "Iltimos username ni to'g'ri kiriting."
            )
        else:
            await update.message.reply_text(
                "⚠️ LeetCode API vaqtincha ishlamayapti. "
                "Username hozircha saqlanmadi, iltimos keyinroq qayta urinib ko'ring."
            )
        return
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Username tekshirishda kutilmagan xato: {type(e).__name__}: {e}"
        )
        return
    
    # Get user info from Telegram
    user = update.effective_user
    telegram_username = user.username if user else None
    telegram_first_name = user.first_name if user else None
    telegram_last_name = user.last_name if user else None
    
    storage.set_username(chat_id, username)
    storage.add_user(
        chat_id=chat_id,
        telegram_username=telegram_username,
        telegram_first_name=telegram_first_name,
        telegram_last_name=telegram_last_name,
    )

    await update.message.reply_text(
        f"✅ Username saqlandi: {username}\n"
        "Endi reminder sozlash uchun: /listremind"
    )

async def username_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id
    u = storage.get_username(chat_id)
    await update.message.reply_text(f"👤 Username: {u or 'bog‘lanmagan'}")

async def tz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.application.bot_data["settings"]
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id
    tz = storage.get_timezone(chat_id, settings.default_tz)
    await update.message.reply_text(f"🕒 Timezone: {tz}")

async def timezone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.application.bot_data["settings"]
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("Misol: /timezone Asia/Tashkent")
        return

    tz = context.args[0].strip()
    if tz not in pytz.all_timezones:
        await update.message.reply_text("❌ Noto‘g‘ri timezone. Misol: Asia/Tashkent")
        return

    storage.set_timezone(chat_id, tz)
    await update.message.reply_text(f"✅ Timezone set: {tz}")

async def listremind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.application.bot_data["settings"]
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id

    times = storage.get_remind_times(chat_id, settings.default_remind_times)
    tz = storage.get_timezone(chat_id, settings.default_tz)

    await update.message.reply_text(
        f"🕒 TZ: {tz}\n"
        f"🔔 Remind: {', '.join(times) if times else 'yo‘q'}\n\n"
        "O‘zgartirish:\n"
        "  /setremind 20:00\n"
        "  /addremind 09:00\n"
        "  /delremind 09:00"
    )

async def setremind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("Misol: /setremind 20:00")
        return

    t = context.args[0].strip()
    if not _valid_hhmm(t):
        await update.message.reply_text("❌ Format noto‘g‘ri. Misol: 20:00")
        return

    storage.set_remind_times(chat_id, [t])
    await update.message.reply_text(f"✅ Remind time set: {t}")

async def addremind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.application.bot_data["settings"]
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("Misol: /addremind 09:00")
        return

    t = context.args[0].strip()
    if not _valid_hhmm(t):
        await update.message.reply_text("❌ Format noto‘g‘ri. Misol: 09:00")
        return

    times = storage.get_remind_times(chat_id, settings.default_remind_times)
    if t not in times:
        times.append(t)
    times = sorted(set(times))
    storage.set_remind_times(chat_id, times)

    await update.message.reply_text(f"✅ Qo‘shildi: {t}\nHozir: {', '.join(times)}")

async def delremind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.application.bot_data["settings"]
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text("Misol: /delremind 09:00")
        return

    t = context.args[0].strip()
    times = storage.get_remind_times(chat_id, settings.default_remind_times)

    if t not in times:
        await update.message.reply_text("❌ Bu vaqt ro‘yxatda yo‘q. /listremind")
        return

    times = [x for x in times if x != t]
    storage.set_remind_times(chat_id, times)

    await update.message.reply_text(
        f"🗑 O‘chirildi: {t}\nHozir: {', '.join(times) if times else 'yo‘q'}"
    )

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.application.bot_data["settings"]
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id

    username = storage.get_username(chat_id)
    if not username:
        await update.message.reply_text("❗ Avval username bog‘la: /setusername your_username")
        return

    tz = storage.get_timezone(chat_id, settings.default_tz)
    allowed, remaining = storage.acquire_external_api_slot(
        chat_id, settings.external_api_cooldown_seconds
    )
    if not allowed:
        await update.message.reply_text(
            f"⏳ Juda tez-tez so'rov yuborildi. Iltimos {remaining} soniyadan keyin qayta urinib ko'ring."
        )
        return

    try:
        ok, info = solved_today(username, tz)
    except RuntimeError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            await update.message.reply_text(
                f"⚠️ LeetCode foydalanuvchi topilmadi: {username}\n"
                f"Username to'g'riligini tekshiring: /setusername"
            )
        else:
            await update.message.reply_text(f"⚠️ Xato: {error_msg}")
        return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Kutilmagan xato: {type(e).__name__}: {e}")
        return

    if ok and info:
        await update.message.reply_text(
            f"🟢✅ Accepted bor!\n"
            f"— {info.title}\n"
            f"⏰ {info.time_hhmm} | 💻 {info.lang}\n"
            f"{problem_link(info.slug)}",
            disable_web_page_preview=True,
        )
    else:
        await update.message.reply_text("🔴 Hozircha Accepted yo‘q.")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = context.application.bot_data["settings"]
    storage: Storage = context.application.bot_data["storage"]
    chat_id = update.effective_chat.id

    username = storage.get_username(chat_id)
    tz = storage.get_timezone(chat_id, settings.default_tz)
    times = storage.get_remind_times(chat_id, settings.default_remind_times)

    if not username:
        await update.message.reply_text(
            "ℹ️ Username bog‘lanmagan.\n"
            "Bog‘lash: /setusername your_username\n"
            f"TZ: {tz}\nRemind: {', '.join(times) if times else 'yo‘q'}"
        )
        return

    allowed, remaining = storage.acquire_external_api_slot(
        chat_id, settings.external_api_cooldown_seconds
    )
    if not allowed:
        await update.message.reply_text(
            "⏳ Tashqi API cooldown faol.\n"
            f"Iltimos {remaining} soniyadan keyin qayta urinib ko'ring.\n"
            f"👤 {username}\nTZ: {tz}\nRemind: {', '.join(times) if times else 'yo‘q'}"
        )
        return

    try:
        ok, info = solved_today(username, tz)
    except RuntimeError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            await update.message.reply_text(
                f"⚠️ LeetCode foydalanuvchi topilmadi: {username}\n"
                f"Username to'g'riligini tekshiring: /setusername\n"
                f"TZ: {tz}\nRemind: {', '.join(times) if times else "yo'q"}"
            )
        else:
            await update.message.reply_text(
                f"⚠️ Xato: {error_msg}\n"
                f"👤 {username}\nTZ: {tz}\nRemind: {', '.join(times) if times else "yo'q"}"
            )
        return
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Kutilmagan xato: {type(e).__name__}: {e}\n"
            f"👤 {username}\nTZ: {tz}\nRemind: {', '.join(times) if times else "yo'q"}"
        )
        return
    
    if ok and info:
        await update.message.reply_text(
            f"🟢 Bugun bajarilgan: {info.title} ({info.time_hhmm})\n{problem_link(info.slug)}",
            disable_web_page_preview=True,
        )
    else:
        await update.message.reply_text(
            "🔴 Bugun hali Accepted yo‘q.\n"
            f"👤 {username}\n"
            f"TZ: {tz}\n"
            f"Remind: {', '.join(times) if times else 'yo‘q'}"
        )

# ---------- Startup ----------
async def _post_init(app: Application):
    settings = app.bot_data["settings"]
    storage: Storage = app.bot_data["storage"]

    if not settings.enable_background_checks:
        return

    # Background scheduler
    scheduler_task = asyncio.create_task(
        run_scheduler(
            bot=app.bot,
            storage=storage,
            default_tz=settings.default_tz,
            default_times=settings.default_remind_times,
            poll_seconds=settings.poll_seconds,
            lc_check_seconds=settings.lc_check_seconds,
            use_celery=settings.use_celery,
        )
    )
    app.bot_data["scheduler_task"] = scheduler_task


async def _post_shutdown(app: Application):
    """Cancel background scheduler task gracefully."""
    task = app.bot_data.get("scheduler_task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

def main():
    settings = get_settings()

    redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
    
    # Initialize PostgreSQL database (optional - won't break if connection fails)
    db = None
    try:
        db = Database(settings.postgresql_url)
    except Exception as e:
        print(f"⚠️ PostgreSQL connection failed (will continue with Redis only): {e}")
    
    storage = Storage(redis_client, db=db)

    app = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    app.bot_data["settings"] = settings
    app.bot_data["storage"] = storage
    app.bot_data["database"] = db  # Store database reference for API

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))

    app.add_handler(CommandHandler("setusername", setusername_cmd))
    app.add_handler(CommandHandler("username", username_cmd))

    app.add_handler(CommandHandler("timezone", timezone_cmd))
    app.add_handler(CommandHandler("tz", tz_cmd))

    app.add_handler(CommandHandler("listremind", listremind_cmd))
    app.add_handler(CommandHandler("setremind", setremind_cmd))
    app.add_handler(CommandHandler("addremind", addremind_cmd))
    app.add_handler(CommandHandler("delremind", delremind_cmd))

    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("status", status_cmd))

    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
