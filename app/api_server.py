"""
FastAPI server for LeetCode Reminder Bot
Run this separately or integrate with bot.py
"""
import uvicorn
from app.config import get_settings
from app.api_app import app

def main():
    """Start FastAPI server"""
    settings = get_settings()
    
    # Start FastAPI server
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
        access_log=True,
    )

if __name__ == "__main__":
    main()
