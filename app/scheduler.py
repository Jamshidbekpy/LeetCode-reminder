from __future__ import annotations

import asyncio
import json
from datetime import datetime
import time
import pytz
from redis import Redis

from telegram import Bot

from app.storage import Storage, DailyState
from app.leetcode import problem_link
from app.config import get_settings

def _is_valid_hhmm(s: str) -> bool:
    if len(s) != 5 or s[2] != ":":
        return False
    hh, mm = s.split(":")
    if not (hh.isdigit() and mm.isdigit()):
        return False
    h, m = int(hh), int(mm)
    return 0 <= h <= 23 and 0 <= m <= 59

def _today_str(tz_name: str) -> str:
    tz = pytz.timezone(tz_name)
    return str(datetime.now(tz).date())

def _dt_today(tz_name: str, hhmm: str) -> datetime:
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    hh, mm = map(int, hhmm.split(":"))
    return now.replace(hour=hh, minute=mm, second=0, microsecond=0)

async def run_scheduler(
    bot: Bot,
    storage: Storage,
    default_tz: str,
    default_times: list[str],
    poll_seconds: int,
    lc_check_seconds: int,
    use_celery: bool = False,
) -> None:
    """
    Har poll'da:
    - barcha userlarni aylanadi
    - remind due bo'lsa yuboradi (har HH:MM ga 1 marta)
    - Accepted bo'lsa congrats yuboradi (1 marta)
    - LeetCode tekshiruvini Celery yoki to'g'ridan-to'g'ri bajaradi
    """
    settings = get_settings()
    redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
    
    while True:
        user_ids = storage.list_users()
        if not user_ids:
            await asyncio.sleep(poll_seconds)
            continue

        for chat_id in user_ids:
            username = storage.get_username(chat_id)
            tz_name = storage.get_timezone(chat_id, default_tz)
            remind_times = storage.get_remind_times(chat_id, default_times)
            remind_times = sorted({t for t in remind_times if _is_valid_hhmm(t)})

            today = _today_str(tz_name)
            state: DailyState = storage.load_state(chat_id, today)

            now_ts = int(time.time())
            ok = False
            info = None

            # LeetCode tekshiruv - Celery yoki to'g'ridan-to'g'ri
            if username:
                if use_celery:
                    # Celery natijasini Redis'dan o'qish
                    result_key = f"lc:check_result:{chat_id}:{today}"
                    result_data = redis_client.get(result_key)
                    
                    if result_data:
                        try:
                            result = json.loads(result_data.decode() if isinstance(result_data, bytes) else result_data)
                            ok = result.get("ok", False)
                            if ok and result.get("info"):
                                info_data = result["info"]
                                from app.leetcode import AcceptedInfo
                                info = AcceptedInfo(
                                    title=info_data.get("title") or "Accepted",
                                    slug=info_data.get("slug") or "",
                                    lang=info_data.get("lang") or "",
                                    time_hhmm=info_data.get("time_hhmm") or "",
                                )
                            # Xatolarni tekshirish
                            error_key = f"lc:check_error:{chat_id}:{today}"
                            error_data = redis_client.get(error_key)
                            if error_data:
                                try:
                                    error = json.loads(error_data.decode() if isinstance(error_data, bytes) else error_data)
                                    error_msg = error.get("error", "")
                                    error_type = error.get("error_type", "")
                                    
                                    # Xatolarni boshqarish
                                    if "not found" in error_msg.lower():
                                        if (now_ts - state.last_error_ts) > 86400:
                                            await bot.send_message(
                                                chat_id=chat_id,
                                                text=f"⚠️ LeetCode foydalanuvchi topilmadi: {username}\n"
                                                     f"Username to'g'riligini tekshiring: /setusername",
                                                disable_web_page_preview=True,
                                            )
                                            state.last_error_ts = now_ts
                                            storage.save_state(chat_id, state)
                                    elif "rate limit" in error_msg.lower() or "blocked" in error_msg.lower():
                                        if (now_ts - state.last_rate_limit_ts) > 3600:
                                            await bot.send_message(
                                                chat_id=chat_id,
                                                text=f"⚠️ LeetCode API cheklov: {error_msg}\n"
                                                     f"Bir oz kutib, keyin qayta urinib ko'ring.",
                                                disable_web_page_preview=True,
                                            )
                                            state.last_rate_limit_ts = now_ts
                                            storage.save_state(chat_id, state)
                                    else:
                                        if (now_ts - state.last_error_ts) > 86400:
                                            await bot.send_message(
                                                chat_id=chat_id,
                                                text=f"⚠️ LeetCode tekshiruv muammo: {error_msg}\n"
                                                     f"Username: {username}",
                                                disable_web_page_preview=True,
                                            )
                                            state.last_error_ts = now_ts
                                            storage.save_state(chat_id, state)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                else:
                    # Eski usul - to'g'ridan-to'g'ri tekshirish
                    should_check = (now_ts - state.last_lc_check_ts) >= lc_check_seconds
                    if should_check or not state.congrats_sent:
                        try:
                            from app.leetcode import solved_today
                            ok, info = solved_today(username, tz_name)
                            state.last_lc_check_ts = now_ts
                            storage.save_state(chat_id, state)
                        except RuntimeError as e:
                            error_msg = str(e)
                            if "not found" in error_msg.lower():
                                if (now_ts - state.last_error_ts) > 86400:
                                    await bot.send_message(
                                        chat_id=chat_id,
                                        text=f"⚠️ LeetCode foydalanuvchi topilmadi: {username}\n"
                                             f"Username to'g'riligini tekshiring: /setusername",
                                        disable_web_page_preview=True,
                                    )
                                    state.last_error_ts = now_ts
                                    storage.save_state(chat_id, state)
                            elif "rate limit" in error_msg.lower() or "blocked" in error_msg.lower():
                                if (now_ts - state.last_rate_limit_ts) > 3600:
                                    await bot.send_message(
                                        chat_id=chat_id,
                                        text=f"⚠️ LeetCode API cheklov: {error_msg}\n"
                                             f"Bir oz kutib, keyin qayta urinib ko'ring.",
                                        disable_web_page_preview=True,
                                    )
                                    state.last_rate_limit_ts = now_ts
                                    storage.save_state(chat_id, state)
                            else:
                                if (now_ts - state.last_error_ts) > 86400:
                                    await bot.send_message(
                                        chat_id=chat_id,
                                        text=f"⚠️ LeetCode tekshiruv muammo: {error_msg}\n"
                                             f"Username: {username}",
                                        disable_web_page_preview=True,
                                    )
                                    state.last_error_ts = now_ts
                                    storage.save_state(chat_id, state)
                            continue
                        except Exception as e:
                            if (now_ts - state.last_error_ts) > 86400:
                                await bot.send_message(
                                    chat_id=chat_id,
                                    text=f"⚠️ Kutilmagan xato: {type(e).__name__}: {e}\n"
                                         f"Username: {username}",
                                    disable_web_page_preview=True,
                                )
                                state.last_error_ts = now_ts
                                storage.save_state(chat_id, state)
                            continue

            # Congrats
            if username and ok and (not state.congrats_sent) and info is not None:
                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "🟢✅ Bugungi target bajarildi!\n"
                        f"— {info.title}\n"
                        f"⏰ {info.time_hhmm} | 💻 {info.lang}\n"
                        f"{problem_link(info.slug)}"
                    ),
                    disable_web_page_preview=True,
                )
                state.congrats_sent = True
                storage.save_state(chat_id, state)

            # Reminder (due bo'lsa yubor) — faqat username bog'langan bo'lsa meaningful
            if username and (not ok) and (not state.congrats_sent):
                tz = pytz.timezone(tz_name)
                now = datetime.now(tz)

                for t in remind_times:
                    if t in state.reminded_times:
                        continue
                    if now >= _dt_today(tz_name, t):
                        await bot.send_message(
                            chat_id=chat_id,
                            text=(
                                f"🔴⏳ Bugun ({tz_name}) hali 1 ta LeetCode ACCEPTED yo'q.\n"
                                f"Eslatma vaqti: {t}\n"
                                "Hozir 1 ta yechib qo'y — yechsang avtomatik 🟢✅ tabrik yuboraman."
                            ),
                            disable_web_page_preview=True,
                        )
                        state.reminded_times.add(t)
                        storage.save_state(chat_id, state)

        await asyncio.sleep(poll_seconds)
