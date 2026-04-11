from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str
    DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/habitual"


    model_config = ConfigDict(
        env_file = ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
