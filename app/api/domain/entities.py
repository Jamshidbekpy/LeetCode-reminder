"""Domain entities - core business objects"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class User:
    """User domain entity"""
    id: int
    telegram_id: int
    telegram_username: Optional[str]
    telegram_first_name: Optional[str]
    telegram_last_name: Optional[str]
    leetcode_username: Optional[str]
    timezone: Optional[str]
    remind_times: list[str]
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime]
    is_active: bool

    def __post_init__(self) -> None:
        """Validate entity after initialization"""
        if self.telegram_id <= 0:
            raise ValueError("telegram_id must be positive")
        if self.remind_times and not all(
            isinstance(t, str) and len(t) == 5 and t[2] == ":" for t in self.remind_times
        ):
            raise ValueError("Invalid remind_times format")


@dataclass(frozen=True)
class UserStats:
    """User statistics domain entity"""
    total_users: int
    active_users: int
    inactive_users: int
    users_with_leetcode: int
    users_by_timezone: dict[str, int]
