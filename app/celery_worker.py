"""
Celery worker va beat ishga tushirish
"""
from app.celery_app import celery_app

if __name__ == "__main__":
    # Celery worker ishga tushirish
    celery_app.worker_main()
