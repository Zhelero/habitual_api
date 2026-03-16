import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base
from app.db.session import engine
from app.api.routers import habits, dashboard
from app.core.exceptions import AppError
from app.core.handlers import app_error_handler
from app.core.middleware import log_requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s - %(message)s",
)

app = FastAPI(title="Habitual API")

app.middleware("http")(log_requests)

app.include_router(habits.router)
app.include_router(dashboard.router)

app.add_exception_handler(AppError, app_error_handler)



#CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"status": "ok"}
