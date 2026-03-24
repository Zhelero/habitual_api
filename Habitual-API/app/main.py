import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import models
from app.db.base import Base
from app.db.session import engine
from app.api.routers import habits, dashboard, auth
from app.core.exceptions import AppError
from app.core.handlers import app_error_handler
from app.core.middleware import log_requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s - %(message)s",
)

app = FastAPI(title="Habitual API")

#CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return {"status": "healthy"}

Base.metadata.create_all(bind=engine)