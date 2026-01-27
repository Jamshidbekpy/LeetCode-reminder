from __future__ import annotations

import json
import time
from datetime import datetime
import pytz
from redis import Redis
from app.celery_app import celery_app
from app.config import get_settings
from app.storage import Storage
from app.leetcode import solved_today

settings = get_settings()


@celery_app.task(name="app.celery_tasks.check_all_users_leetcode", bind=True)
def check_all_users_leetcode(self):
    """
    Celery task: Barcha userlarni LeetCode API'dan tekshirish.
    Natijalar Redis'ga yoziladi, bot scheduler ularni o'qib Telegram xabar yuboradi.
    """
    redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
    storage = Storage(redis_client, db=None)  # Celery task'da PostgreSQL kerak emas
    
    user_ids = storage.list_users()
    if not user_ids:
        return {"checked": 0, "success": 0, "errors": 0}
    
    checked = 0
    success = 0
    errors = 0
    
    for chat_id in user_ids:
        try:
            username = storage.get_username(chat_id)
            if not username:
                continue
            
            tz_name = storage.get_timezone(chat_id, settings.default_tz)
            today = datetime.now(pytz.timezone(tz_name)).date().isoformat()
            
            # LeetCode tekshiruv
            try:
                ok, info = solved_today(username, tz_name)
                
                # Natijani Redis'ga yozish (bot scheduler o'qiydi)
                result_key = f"lc:check_result:{chat_id}:{today}"
                result_data = {
                    "ok": ok,
                    "info": {
                        "title": info.title if info else None,
                        "slug": info.slug if info else None,
                        "lang": info.lang if info else None,
                        "time_hhmm": info.time_hhmm if info else None,
                    } if info else None,
                    "checked_at": int(time.time()),
                    "username": username,
                }
                
                redis_client.setex(
                    result_key,
                    86400,  # 24 soat TTL
                    json.dumps(result_data, ensure_ascii=False)
                )
                
                success += 1
            except Exception as e:
                # Xatoni Redis'ga yozish
                error_key = f"lc:check_error:{chat_id}:{today}"
                error_data = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "checked_at": int(time.time()),
                    "username": username,
                }
                redis_client.setex(
                    error_key,
                    86400,
                    json.dumps(error_data, ensure_ascii=False)
                )
                errors += 1
            
            checked += 1
            
        except Exception as e:
            errors += 1
            continue
    
    return {
        "checked": checked,
        "success": success,
        "errors": errors,
        "timestamp": int(time.time()),
    }
