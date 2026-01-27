"""Repository implementations - concrete data access layer"""
from __future__ import annotations

from typing import Optional
from app.api.domain.entities import User, UserStats
from app.api.domain.repositories import UserRepository
from app.database import Database as PostgresDatabase


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository"""

    def __init__(self, db: PostgresDatabase) -> None:
        self.db = db

    def _to_domain_entity(self, db_user) -> User:
        """Convert database model to domain entity"""
        return User(
            id=db_user.id,
            telegram_id=db_user.telegram_id,
            telegram_username=db_user.telegram_username,
            telegram_first_name=db_user.telegram_first_name,
            telegram_last_name=db_user.telegram_last_name,
            leetcode_username=db_user.leetcode_username,
            timezone=db_user.timezone,
            remind_times=db_user.remind_times or [],
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            last_active_at=db_user.last_active_at,
            is_active=bool(db_user.is_active),
        )

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        db_user = self.db.get_user_by_telegram_id(telegram_id)
        if db_user is None:
            return None
        return self._to_domain_entity(db_user)

    def get_all(self, active_only: bool = True) -> list[User]:
        """Get all users"""
        db_users = self.db.get_all_users(active_only=active_only)
        return [self._to_domain_entity(user) for user in db_users]

    def get_by_leetcode_username(self, leetcode_username: str) -> list[User]:
        """Get users by LeetCode username"""
        db_users = self.db.get_users_by_leetcode_username(leetcode_username)
        return [self._to_domain_entity(user) for user in db_users]

    def get_stats(self) -> UserStats:
        """Get user statistics"""
        all_users = self.db.get_all_users(active_only=False)
        active_users = self.db.get_all_users(active_only=True)

        users_with_leetcode = sum(1 for u in active_users if u.leetcode_username)

        timezones: dict[str, int] = {}
        for user in active_users:
            tz = user.timezone or "Unknown"
            timezones[tz] = timezones.get(tz, 0) + 1

        return UserStats(
            total_users=len(all_users),
            active_users=len(active_users),
            inactive_users=len(all_users) - len(active_users),
            users_with_leetcode=users_with_leetcode,
            users_by_timezone=timezones,
        )
