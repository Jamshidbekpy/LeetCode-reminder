from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
from app.database import Database, User

app = FastAPI(
    title="LeetCode Reminder Bot API",
    description="API for accessing user data from LeetCode Reminder Bot",
    version="1.0.0",
)

# Global database instance (will be set during startup)
db: Optional[Database] = None


class UserResponse(BaseModel):
    """User response model"""
    id: int
    telegram_id: int
    telegram_username: Optional[str]
    telegram_first_name: Optional[str]
    telegram_last_name: Optional[str]
    leetcode_username: Optional[str]
    timezone: Optional[str]
    remind_times: Optional[List[str]]
    created_at: Optional[str]
    updated_at: Optional[str]
    last_active_at: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response model"""
    total: int
    users: List[UserResponse]


@app.on_event("startup")
async def startup_event():
    """Initialize database connection"""
    global db
    # Database will be set by the main application
    pass


def set_database(database: Database):
    """Set database instance"""
    global db
    db = database


@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "message": "LeetCode Reminder Bot API",
        "version": "1.0.0",
        "endpoints": {
            "users": "/api/users",
            "user_by_telegram_id": "/api/users/telegram/{telegram_id}",
            "users_by_leetcode": "/api/users/leetcode/{leetcode_username}",
            "health": "/api/health",
        }
    }


@app.get("/api/health", tags=["General"])
async def health_check():
    """Health check endpoint"""
    if db is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": "Database not initialized"}
        )
    
    try:
        # Try to query database
        users = db.get_all_users(active_only=False)
        return {
            "status": "healthy",
            "database": "connected",
            "total_users": len(users)
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": str(e)}
        )


@app.get("/api/users", response_model=UserListResponse, tags=["Users"])
async def get_all_users(
    active_only: bool = Query(True, description="Return only active users"),
    limit: Optional[int] = Query(None, description="Limit number of results"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """
    Get all users
    
    - **active_only**: Return only active users (default: True)
    - **limit**: Limit number of results
    - **offset**: Offset for pagination
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        users = db.get_all_users(active_only=active_only)
        
        # Apply pagination
        total = len(users)
        if offset > 0:
            users = users[offset:]
        if limit:
            users = users[:limit]
        
        return UserListResponse(
            total=total,
            users=[UserResponse(**user.to_dict()) for user in users]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@app.get("/api/users/telegram/{telegram_id}", response_model=UserResponse, tags=["Users"])
async def get_user_by_telegram_id(telegram_id: int):
    """
    Get user by Telegram ID
    
    - **telegram_id**: Telegram user ID
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        user = db.get_user_by_telegram_id(telegram_id)
        if user is None:
            raise HTTPException(status_code=404, detail=f"User with telegram_id {telegram_id} not found")
        
        return UserResponse(**user.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")


@app.get("/api/users/leetcode/{leetcode_username}", response_model=UserListResponse, tags=["Users"])
async def get_users_by_leetcode_username(leetcode_username: str):
    """
    Get users by LeetCode username
    
    - **leetcode_username**: LeetCode username
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        users = db.get_users_by_leetcode_username(leetcode_username)
        
        return UserListResponse(
            total=len(users),
            users=[UserResponse(**user.to_dict()) for user in users]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


@app.get("/api/stats", tags=["Statistics"])
async def get_stats():
    """Get statistics about users"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        all_users = db.get_all_users(active_only=False)
        active_users = db.get_all_users(active_only=True)
        
        # Count users with LeetCode username
        users_with_leetcode = sum(1 for u in active_users if u.leetcode_username)
        
        # Count users by timezone
        timezones = {}
        for user in active_users:
            tz = user.timezone or "Unknown"
            timezones[tz] = timezones.get(tz, 0) + 1
        
        return {
            "total_users": len(all_users),
            "active_users": len(active_users),
            "inactive_users": len(all_users) - len(active_users),
            "users_with_leetcode": users_with_leetcode,
            "users_by_timezone": timezones,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
