from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import uuid

from app.core.exceptions import InvalidTokenError
from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

def create_token(data: dict, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)

    to_encode = data.copy()
    to_encode.update({
        "exp": now + expires_delta,
        "iat": now,
        "nbf": now,
        "jti": str(uuid.uuid4()),
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise InvalidTokenError(str(e))

    if expected_type and payload.get("type") != expected_type:
        raise InvalidTokenError()

    if "sub" not in payload:
        raise InvalidTokenError("Missing subject")

    return payload

def create_access_token(data: dict) -> str:
    return create_token(
        {**data, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

def create_refresh_token(data: dict) -> str:
    return create_token(
        {**data, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )