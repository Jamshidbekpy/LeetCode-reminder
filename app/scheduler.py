from __future__ import annotations

import asyncio
from datetime import datetime
import time
import pytz

from telegram import Bot

from app.storage import Storage, DailyState
from app.leetcode import solved_today, problem_link

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
) -> None:
    """
    Har poll'da:
    - barcha userlarni aylanadi
    - remind due bo'lsa yuboradi (har HH:MM ga 1 marta)
    - Accepted bo'lsa congrats yuboradi (1 marta)
    - LeetCode tekshiruvini har user uchun throttle qiladi (lc_check_seconds)
    """
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

            # LeetCode check throttle
            now_ts = int(time.time())
            should_check = (now_ts - state.last_lc_check_ts) >= lc_check_seconds
            ok = False
            info = None

            if username and (should_check or not state.congrats_sent):
                try:
                    ok, info = solved_today(username, tz_name)
                    state.last_lc_check_ts = now_ts
                    storage.save_state(chat_id, state)
                except Exception as e:
                    # xatoni spam qilmaymiz: faqat kuniga 1 marta yoki tekshiruv intervalida yubormaslik ham mumkin
                    # hozircha: 1 marta xabar yuborib qo'yamiz, lekin juda ko'p bo'lsa lc_check_seconds oshirasan
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ LeetCode tekshiruv muammo: {e}\nUsername: {username or 'bog‘lanmagan'}",
                        disable_web_page_preview=True,
                    )
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
                                f"🔴⏳ Bugun ({tz_name}) hali 1 ta LeetCode ACCEPTED yo‘q.\n"
                                f"Eslatma vaqti: {t}\n"
                                "Hozir 1 ta yechib qo‘y — yechsang avtomatik 🟢✅ tabrik yuboraman."
                            ),
                            disable_web_page_preview=True,
                        )
                        state.reminded_times.add(t)
                        storage.save_state(chat_id, state)

        await asyncio.sleep(poll_seconds)
