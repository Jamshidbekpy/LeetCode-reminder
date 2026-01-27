from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from contextlib import contextmanager

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Production/Docker: retry postgres connection (postgres may still be starting)
_DB_CONNECT_RETRIES = 5
_DB_CONNECT_DELAY_SEC = 2


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""
    pass


class User(Base):
    """PostgreSQL user table model (SQLAlchemy 2.0 style)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    leetcode_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    remind_times: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # List of HH:MM strings
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1 = active, 0 = inactive

    def to_dict(self) -> dict:
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "telegram_username": self.telegram_username,
            "telegram_first_name": self.telegram_first_name,
            "telegram_last_name": self.telegram_last_name,
            "leetcode_username": self.leetcode_username,
            "timezone": self.timezone,
            "remind_times": self.remind_times,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "is_active": bool(self.is_active),
        }


class Database:
    """PostgreSQL database manager"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        last_err: Optional[Exception] = None
        for attempt in range(1, _DB_CONNECT_RETRIES + 1):
            try:
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                Base.metadata.create_all(bind=self.engine)
                return
            except Exception as e:
                last_err = e
                if attempt < _DB_CONNECT_RETRIES:
                    time.sleep(_DB_CONNECT_DELAY_SEC)
        if last_err:
            raise last_err
    
    @contextmanager
    def get_session(self):
        """Get database session context manager"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID"""
        with self.get_session() as session:
            return session.execute(
                select(User).where(User.telegram_id == telegram_id)
            ).scalar_one_or_none()
    
    def create_or_update_user(
        self,
        telegram_id: int,
        telegram_username: Optional[str] = None,
        telegram_first_name: Optional[str] = None,
        telegram_last_name: Optional[str] = None,
        leetcode_username: Optional[str] = None,
        timezone: Optional[str] = None,
        remind_times: Optional[list[str]] = None,
        is_active: bool = True,
    ) -> User:
        """Create or update user"""
        with self.get_session() as session:
            user = session.execute(
                select(User).where(User.telegram_id == telegram_id)
            ).scalar_one_or_none()

            if user:
                # Update existing user
                if telegram_username is not None:
                    user.telegram_username = telegram_username
                if telegram_first_name is not None:
                    user.telegram_first_name = telegram_first_name
                if telegram_last_name is not None:
                    user.telegram_last_name = telegram_last_name
                if leetcode_username is not None:
                    user.leetcode_username = leetcode_username
                if timezone is not None:
                    user.timezone = timezone
                if remind_times is not None:
                    user.remind_times = remind_times
                user.is_active = 1 if is_active else 0
                user.last_active_at = _utc_now()
                user.updated_at = _utc_now()
            else:
                # Create new user
                user = User(
                    telegram_id=telegram_id,
                    telegram_username=telegram_username,
                    telegram_first_name=telegram_first_name,
                    telegram_last_name=telegram_last_name,
                    leetcode_username=leetcode_username,
                    timezone=timezone,
                    remind_times=remind_times or [],
                    is_active=1 if is_active else 0,
                    last_active_at=_utc_now(),
                )
                session.add(user)

            session.commit()
            session.refresh(user)
            return user
    
    def get_all_users(self, active_only: bool = True) -> list[User]:
        """Get all users"""
        with self.get_session() as session:
            stmt = select(User)
            if active_only:
                stmt = stmt.where(User.is_active == 1)
            return list(session.execute(stmt).scalars().all())
    
    def get_users_by_leetcode_username(self, leetcode_username: str) -> list[User]:
        """Get users by LeetCode username"""
        with self.get_session() as session:
            stmt = select(User).where(
                User.leetcode_username == leetcode_username,
                User.is_active == 1,
            )
            return list(session.execute(stmt).scalars().all())
