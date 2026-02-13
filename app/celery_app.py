from __future__ import annotations

from celery import Celery
from celery.schedules import crontab, schedule
from app.config import get_settings

settings = get_settings()

# Celery app yaratish
celery_app = Celery(
    "leetcode_bot",
    broker=settings.redis_url,  # Redis broker
    backend=settings.redis_url,  # Redis backend
)

# Celery sozlamalari
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minut timeout (ko'p userlar bo'lsa)
    task_soft_time_limit=280,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    # Celery 6.0+ compatibility
    broker_connection_retry_on_startup=True,
)

# Celery Beat periodic tasks
# Interval'ni sozlamalardan olish (sekundlarda)
check_interval_seconds = max(300, settings.celery_check_interval)  # Minimum 5 minut

# Schedule file /tmp da (read_only container uchun)
celery_app.conf.beat_schedule_filename = "/tmp/celerybeat-schedule"

celery_app.conf.beat_schedule = {
    "check-leetcode-users": {
        "task": "app.celery_tasks.check_all_users_leetcode",
        "schedule": schedule(run_every=check_interval_seconds),  # Har N sekundda bir marta
    },
}

# Timezone sozlash
celery_app.conf.timezone = "UTC"
