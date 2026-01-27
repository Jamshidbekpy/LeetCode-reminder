"""Security utilities and middleware"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class SecurityConfig:
    """Security configuration"""

    @staticmethod
    def generate_api_key() -> str:
        """Generate secure API key"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hash_obj.hex(), salt

    @staticmethod
    def verify_password(password: str, hash_value: str, salt: str) -> bool:
        """Verify password"""
        new_hash, _ = SecurityConfig.hash_password(password, salt)
        return hmac.compare_digest(new_hash, hash_value)

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)


class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)"""

    def __init__(self) -> None:
        self.requests: dict[str, list[float]] = {}

    def is_allowed(self, identifier: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed"""
        now = time.time()
        if identifier not in self.requests:
            self.requests[identifier] = []

        # Remove old requests
        self.requests[identifier] = [
            req_time
            for req_time in self.requests[identifier]
            if now - req_time < window_seconds
        ]

        # Check limit
        if len(self.requests[identifier]) >= max_requests:
            return False

        # Add current request
        self.requests[identifier].append(now)
        return True


security_bearer = HTTPBearer(auto_error=False)


async def verify_api_key(request: Request) -> Optional[str]:
    """Verify API key from header"""
    # In production, check against database or environment
    api_key = request.headers.get("X-API-Key")
    expected_key = None  # Load from config

    if expected_key and api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key
