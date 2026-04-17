import logging
import uuid

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError

from app.core.exceptions import InvalidTokenError, TokenRevokedError
from app.core.config import settings

logger = logging.getLogger("app.jwt")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def create_token(data: dict, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)

    to_encode = data.copy()
    to_encode.update(
        {
            "exp": now + expires_delta,
            "iat": now,
            "nbf": now,
            "jti": str(uuid.uuid4()),
        }
    )

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.debug("Token created type=%s", to_encode.get("type"))

    return token


def decode_token(
    token: str,
    expected_type: str | None = None,
    blacklist_repo=None,
) -> dict:
    if not token:
        logger.warning("Empty token received")
        raise InvalidTokenError("Empty token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        logger.info("Expired token")
        raise InvalidTokenError("Expired token")
    except JWTError:
        logger.warning("Invalid token")
        raise InvalidTokenError("Invalid token")

    if "sub" not in payload:
        logger.warning("Token missing subject")
        raise InvalidTokenError("Missing subject")

    token_type = payload.get("type")
    if not token_type:
        logger.warning("Token missing type")
        raise InvalidTokenError("Missing token type")

    if expected_type and token_type != expected_type:
        logger.warning(
            "Invalid token: expected type %s but received type %s",
            expected_type,
            token_type,
        )
        raise InvalidTokenError("Invalid token type")

    jti = get_jti(payload)

    if blacklist_repo and blacklist_repo.is_blacklisted(jti):
        logger.info("Revoked token")
        raise TokenRevokedError()

    return payload


def create_access_token(data: dict) -> str:
    return create_token(
        {**data, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(data: dict) -> str:
    return create_token(
        {**data, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def get_jti(payload: dict) -> str:
    try:
        return payload["jti"]
    except KeyError:
        logger.warning("Token missing jti")
        raise InvalidTokenError("Missing jti")
