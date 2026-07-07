import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.api.routers import habits, dashboard, auth
from app.core.exceptions import AppError
from app.core.handlers import app_error_handler, rate_limit_exceeded_handler
from app.core.middleware import log_requests

setup_logging(settings.LOG_LEVEL)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Habitual API")
    logger.info("Log level: %s", settings.LOG_LEVEL)
    logger.info("Database: %s", settings.DATABASE_URL.split("@")[-1])
    yield


app = FastAPI(title="Habitual API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — explicit allow-list. Configure via the CORS_ORIGINS env var
# (comma-separated) rather than "*", since credentialed cross-origin
# requests from an arbitrary site are otherwise possible.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(log_requests)

app.include_router(habits.router, tags=["habits"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(auth.router, tags=["auth"])

app.add_exception_handler(AppError, app_error_handler)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Habitual API",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
