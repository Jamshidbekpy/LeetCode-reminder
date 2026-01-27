"""Repository interfaces - abstract data access layer"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from app.api.domain.entities import User, UserStats


class UserRepository(ABC):
    """Abstract user repository interface"""

    @abstractmethod
    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        pass

    @abstractmethod
    def get_all(self, active_only: bool = True) -> list[User]:
        """Get all users"""
        pass

    @abstractmethod
    def get_by_leetcode_username(self, leetcode_username: str) -> list[User]:
        """Get users by LeetCode username"""
        pass

    @abstractmethod
    def get_stats(self) -> UserStats:
        """Get user statistics"""
        pass
