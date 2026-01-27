"""FastAPI application with clean architecture"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import get_settings
from app.database import Database
from app.api.interfaces.controllers import router
from app.api.interfaces.dependencies import set_user_repository
from app.api.infrastructure.repositories import PostgresUserRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="LeetCode Reminder Bot API",
    description="Production-ready API for LeetCode Reminder Bot with clean architecture",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add rate limiter exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Configure properly in production
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting API application...")
    try:
        db = Database(settings.postgresql_url)
        repository = PostgresUserRepository(db)
        set_user_repository(repository)
        logger.info("✅ PostgreSQL connected and repository initialized")
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        logger.warning("⚠️ API will run but database operations will fail")

    yield

    # Shutdown
    logger.info("Shutting down API application...")


app.router.lifespan_context = lifespan

# Include routers
app.include_router(router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "LeetCode Reminder Bot API",
        "version": "2.0.0",
        "architecture": "Clean Architecture",
        "endpoints": {
            "users": "/api/users",
            "user_by_telegram_id": "/api/users/telegram/{telegram_id}",
            "users_by_leetcode": "/api/users/leetcode/{leetcode_username}",
            "stats": "/api/stats",
            "health": "/api/health",
            "docs": "/docs",
        },
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        },
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response
