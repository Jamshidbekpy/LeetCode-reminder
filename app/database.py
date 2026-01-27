from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

Base = declarative_base()


class User(Base):
    """PostgreSQL user table model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255), nullable=True)
    telegram_first_name = Column(String(255), nullable=True)
    telegram_last_name = Column(String(255), nullable=True)
    leetcode_username = Column(String(255), nullable=True, index=True)
    timezone = Column(String(100), nullable=True)
    remind_times = Column(JSON, nullable=True)  # List of HH:MM strings
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1, nullable=False)  # 1 = active, 0 = inactive

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
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
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
            return session.query(User).filter(User.telegram_id == telegram_id).first()
    
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
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            
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
                user.last_active_at = datetime.utcnow()
                user.updated_at = datetime.utcnow()
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
                    last_active_at=datetime.utcnow(),
                )
                session.add(user)
            
            session.commit()
            session.refresh(user)
            return user
    
    def get_all_users(self, active_only: bool = True) -> list[User]:
        """Get all users"""
        with self.get_session() as session:
            query = session.query(User)
            if active_only:
                query = query.filter(User.is_active == 1)
            return query.all()
    
    def get_users_by_leetcode_username(self, leetcode_username: str) -> list[User]:
        """Get users by LeetCode username"""
        with self.get_session() as session:
            return session.query(User).filter(
                User.leetcode_username == leetcode_username,
                User.is_active == 1
            ).all()
