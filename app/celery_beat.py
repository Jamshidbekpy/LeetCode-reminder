"""
Celery Beat scheduler ishga tushirish
"""
from app.celery_app import celery_app

if __name__ == "__main__":
    # Celery Beat ishga tushirish
    celery_app.start(["celery", "beat", "-l", "info"])
