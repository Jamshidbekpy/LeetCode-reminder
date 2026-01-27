"""FastAPI dependencies"""
from __future__ import annotations

from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.api.infrastructure.repositories import PostgresUserRepository
from app.api.domain.repositories import UserRepository

# API Key security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Global database instance (set during startup)
_db: Optional[PostgresUserRepository] = None


def get_user_repository() -> UserRepository:
    """Dependency: Get user repository"""
    if _db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized",
        )
    return _db


def set_user_repository(repository: PostgresUserRepository) -> None:
    """Set user repository instance"""
    global _db
    _db = repository


def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> bool:
    """Verify API key (optional authentication)"""
    # In production, check against environment variable or database
    expected_key = None  # Should be loaded from config
    if expected_key is None:
        # If no API key configured, allow access (for development)
        return True
    return api_key == expected_key
