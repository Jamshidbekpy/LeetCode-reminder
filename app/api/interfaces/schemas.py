"""API schemas - request/response models"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    telegram_id: int
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    telegram_last_name: Optional[str] = None
    leetcode_username: Optional[str] = None
    timezone: Optional[str] = None
    remind_times: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    last_active_at: Optional[str] = None
    is_active: bool

    @validator("remind_times", pre=True)
    def validate_remind_times(cls, v):
        """Validate remind times format"""
        if not isinstance(v, list):
            return []
        return [str(t) for t in v if isinstance(t, str)]

    class Config:
        """Pydantic config"""
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response schema"""
    total: int
    users: list[UserResponse]


class UserStatsResponse(BaseModel):
    """User statistics response schema"""
    total_users: int
    active_users: int
    inactive_users: int
    users_with_leetcode: int
    users_by_timezone: dict[str, int]


class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    database: Optional[str] = None
    total_users: Optional[int] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    error_code: Optional[str] = None
