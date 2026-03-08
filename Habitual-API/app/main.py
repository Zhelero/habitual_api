from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.sql.functions import user

from app.db.base import Base
from app.db.session import engine
from app.api.routers import habits

app = FastAPI(title="Habitual API")

app.include_router(habits.router)

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
    return {"message": "What's new with your habits?"}
