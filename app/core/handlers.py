import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError):
    logger.warning(
        "AppError %s %s -> %s (%s)",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(
        "Rate limit exceeded %s %s -> %s",
        request.method,
        request.url.path,
        exc.detail,
    )

    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )
