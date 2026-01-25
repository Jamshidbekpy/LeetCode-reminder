import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    bot_token: str
    redis_url: str
    poll_seconds: int
    lc_check_seconds: int
    default_tz: str
    default_remind_times: list[str]

def _split_times(s: str) -> list[str]:
    s = (s or "").strip()
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]

def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise SystemExit("BOT_TOKEN .env da bo‘lishi shart.")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()

    poll_seconds = int(os.getenv("POLL_SECONDS", "30"))
    lc_check_seconds = int(os.getenv("LC_CHECK_SECONDS", "300"))

    default_tz = os.getenv("DEFAULT_TZ", "Asia/Tashkent").strip()
    default_remind_times = _split_times(os.getenv("DEFAULT_REMIND_TIMES", "20:00"))

    return Settings(
        bot_token=bot_token,
        redis_url=redis_url,
        poll_seconds=poll_seconds,
        lc_check_seconds=lc_check_seconds,
        default_tz=default_tz,
        default_remind_times=default_remind_times,
    )
