"""Use cases - business logic layer"""
from __future__ import annotations

from typing import Optional
from app.api.domain.entities import User, UserStats
from app.api.domain.repositories import UserRepository


class GetUserByTelegramIdUseCase:
    """Use case for getting user by Telegram ID"""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def execute(self, telegram_id: int) -> Optional[User]:
        """Execute use case"""
        if telegram_id <= 0:
            raise ValueError("telegram_id must be positive")
        return self.repository.get_by_telegram_id(telegram_id)


class GetAllUsersUseCase:
    """Use case for getting all users"""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def execute(
        self, active_only: bool = True, limit: Optional[int] = None, offset: int = 0
    ) -> tuple[list[User], int]:
        """Execute use case"""
        if offset < 0:
            raise ValueError("offset must be non-negative")
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")

        users = self.repository.get_all(active_only=active_only)
        total = len(users)

        if offset > 0:
            users = users[offset:]
        if limit:
            users = users[:limit]

        return users, total


class GetUsersByLeetCodeUsernameUseCase:
    """Use case for getting users by LeetCode username"""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def execute(self, leetcode_username: str) -> list[User]:
        """Execute use case"""
        if not leetcode_username or not leetcode_username.strip():
            raise ValueError("leetcode_username cannot be empty")
        return self.repository.get_by_leetcode_username(leetcode_username.strip())


class GetUserStatsUseCase:
    """Use case for getting user statistics"""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def execute(self) -> UserStats:
        """Execute use case"""
        return self.repository.get_stats()
