import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Settings:
    bot_token: str
    redis_url: str
    postgresql_url: str
    poll_seconds: int
    lc_check_seconds: int
    default_tz: str
    default_remind_times: list[str]
    api_host: str
    api_port: int
    celery_check_interval: int  # Celery Beat interval (seconds)
    use_celery: bool  # Celery ishlatish yoki yo'q
    enable_background_checks: bool  # Scheduler orqali tashqi API tekshirish
    external_api_cooldown_seconds: int  # /check va /status uchun cooldown
    log_level: str  # Logging level
    log_file: str | None  # Log file path (optional)

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
    
    postgresql_url = os.getenv(
        "POSTGRESQL_URL",
        "postgresql://postgres:postgres@localhost:5432/leetcode_bot"
    ).strip()

    poll_seconds = int(os.getenv("POLL_SECONDS", "60"))
    lc_check_seconds = int(os.getenv("LC_CHECK_SECONDS", "1800"))

    default_tz = os.getenv("DEFAULT_TZ", "Asia/Tashkent").strip()
    default_remind_times = _split_times(os.getenv("DEFAULT_REMIND_TIMES", "20:00"))
    
    api_host = os.getenv("API_HOST", "0.0.0.0").strip()
    api_port = int(os.getenv("API_PORT", "8000"))
    
    # Celery sozlamalari
    celery_check_interval = int(os.getenv("CELERY_CHECK_INTERVAL", "1800"))  # Default: 30 minut
    use_celery = os.getenv("USE_CELERY", "false").lower() in ("true", "1", "yes")
    enable_background_checks = os.getenv("ENABLE_BACKGROUND_CHECKS", "false").lower() in ("true", "1", "yes")
    external_api_cooldown_seconds = int(os.getenv("EXTERNAL_API_COOLDOWN_SECONDS", "120"))
    
    # Logging
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    log_file = os.getenv("LOG_FILE", "").strip() or None

    logger.info(f"Settings loaded: Redis={redis_url[:20]}..., PostgreSQL={postgresql_url[:30]}...")

    return Settings(
        bot_token=bot_token,
        redis_url=redis_url,
        postgresql_url=postgresql_url,
        poll_seconds=poll_seconds,
        lc_check_seconds=lc_check_seconds,
        default_tz=default_tz,
        default_remind_times=default_remind_times,
        api_host=api_host,
        api_port=api_port,
        celery_check_interval=celery_check_interval,
        use_celery=use_celery,
        enable_background_checks=enable_background_checks,
        external_api_cooldown_seconds=external_api_cooldown_seconds,
        log_level=log_level,
        log_file=log_file,
    )
