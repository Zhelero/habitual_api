from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import uuid

from app.core.exceptions import InvalidTokenError, TokenRevokedError
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

def decode_token(
        token: str,
        expected_type: str | None = None,
        blacklist_repo=None,
) -> dict:
    if not token:
        raise InvalidTokenError("Empty token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise InvalidTokenError(str(e))

    if "sub" not in payload:
        raise InvalidTokenError("Missing subject")

    token_type=payload.get("type")
    if not token_type:
        raise InvalidTokenError("Missing token type")

    jti = get_jti(payload)

    if expected_type and token_type != expected_type:
        raise InvalidTokenError("Invalid token type")

    if blacklist_repo and blacklist_repo.is_blacklisted(jti):
        raise TokenRevokedError()

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

# HELPER

def get_jti(payload:dict) -> str:
    jti = payload.get("jti")
    if not jti:
        raise InvalidTokenError("Missing jti")
    return jti