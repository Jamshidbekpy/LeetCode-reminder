"""API controllers - request handlers"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.use_cases.user_use_cases import (
    GetUserByTelegramIdUseCase,
    GetAllUsersUseCase,
    GetUsersByLeetCodeUsernameUseCase,
    GetUserStatsUseCase,
)
from app.api.interfaces.schemas import (
    UserResponse,
    UserListResponse,
    UserStatsResponse,
    HealthResponse,
    ErrorResponse,
)
from app.api.interfaces.dependencies import get_user_repository
from app.api.domain.repositories import UserRepository

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Router
router = APIRouter(prefix="/api", tags=["API"])


def _user_to_response(user) -> UserResponse:
    """Convert domain entity to response schema"""
    return UserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
        telegram_first_name=user.telegram_first_name,
        telegram_last_name=user.telegram_last_name,
        leetcode_username=user.leetcode_username,
        timezone=user.timezone,
        remind_times=user.remind_times,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
        last_active_at=user.last_active_at.isoformat() if user.last_active_at else None,
        is_active=user.is_active,
    )


@router.get("/health", response_model=HealthResponse, tags=["Health"])
@limiter.limit("30/minute")
async def health_check(request: Request, repository: UserRepository = Depends(get_user_repository)):
    """Health check endpoint"""
    try:
        users = repository.get_all(active_only=False)
        return HealthResponse(
            status="healthy",
            database="connected",
            total_users=len(users),
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            message=str(e),
        )


@router.get("/users", response_model=UserListResponse, tags=["Users"])
@limiter.limit("60/minute")
async def get_all_users(
    request: Request,
    active_only: bool = Query(True, description="Return only active users"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    repository: UserRepository = Depends(get_user_repository),
):
    """Get all users with pagination"""
    try:
        use_case = GetAllUsersUseCase(repository)
        users, total = use_case.execute(active_only=active_only, limit=limit, offset=offset)
        return UserListResponse(
            total=total,
            users=[_user_to_response(user) for user in users],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}",
        )


@router.get(
    "/users/telegram/{telegram_id}",
    response_model=UserResponse,
    tags=["Users"],
)
@limiter.limit("60/minute")
async def get_user_by_telegram_id(
    request: Request,
    telegram_id: int,
    repository: UserRepository = Depends(get_user_repository),
):
    """Get user by Telegram ID"""
    try:
        use_case = GetUserByTelegramIdUseCase(repository)
        user = use_case.execute(telegram_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with telegram_id {telegram_id} not found",
            )
        return _user_to_response(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}",
        )


@router.get(
    "/users/leetcode/{leetcode_username}",
    response_model=UserListResponse,
    tags=["Users"],
)
@limiter.limit("60/minute")
async def get_users_by_leetcode_username(
    request: Request,
    leetcode_username: str,
    repository: UserRepository = Depends(get_user_repository),
):
    """Get users by LeetCode username"""
    try:
        use_case = GetUsersByLeetCodeUsernameUseCase(repository)
        users = use_case.execute(leetcode_username)
        return UserListResponse(
            total=len(users),
            users=[_user_to_response(user) for user in users],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching users: {str(e)}",
        )


@router.get("/stats", response_model=UserStatsResponse, tags=["Statistics"])
@limiter.limit("30/minute")
async def get_stats(request: Request, repository: UserRepository = Depends(get_user_repository)):
    """Get user statistics"""
    try:
        use_case = GetUserStatsUseCase(repository)
        stats = use_case.execute()
        return UserStatsResponse(
            total_users=stats.total_users,
            active_users=stats.active_users,
            inactive_users=stats.inactive_users,
            users_with_leetcode=stats.users_with_leetcode,
            users_by_timezone=stats.users_by_timezone,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stats: {str(e)}",
        )
