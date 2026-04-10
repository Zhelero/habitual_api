import pytest
from datetime import timedelta, datetime, timezone
from jose import jwt

from app.core.config import settings
from app.core.jwt import decode_token, create_access_token, create_token
from app.core.exceptions import InvalidTokenError, TokenRevokedError
from app.repositories.blacklist_repository import TokenBlacklistRepository

def test_jwt_invalid_token():
    with pytest.raises(InvalidTokenError):
        decode_token("invalid_token")

def test_jwt_missing_sub():
    token = create_access_token({})
    with pytest.raises(InvalidTokenError):
        decode_token(token)

def test_jwt_wrong_type():
    token = create_access_token({"sub": "1"})
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="refresh")

def test_jwt_missing_type():
    from app.core.jwt import create_token
    from datetime import timedelta

    token = create_token({"sub": "1"}, timedelta(minutes=5))
    with pytest.raises(InvalidTokenError):
        decode_token(token)

def test_jwt_missing_jti():
    from jose import jwt
    from app.core.config import settings

    payload = {"sub": "1", "type": "access"}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_token(token)

def test_jwt_blacklisted(db):
    from datetime import datetime, timezone

    repo = TokenBlacklistRepository(db)

    token = create_access_token({"sub": "1"})
    payload = decode_token(token)

    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    repo.add(payload["jti"], expires_at)

    with pytest.raises(TokenRevokedError):
        decode_token(token, blacklist_repo=repo)

def test_jwt_expired_token():
    token = create_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))

    with pytest.raises(InvalidTokenError):
        decode_token(token)

def test_jwt_wrong_secret():
    token = create_access_token({"sub": "1"})

    payload = jwt.decode(
        token,
        "WRONG_SECRET",
        algorithms=[settings.ALGORITHM],
        options={"verify_signature": False}
    )

    broken = jwt.encode(payload, "WRONG_SECRET", algorithm=settings.ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_token(broken)

def test_jwt_no_signature():
    token = create_access_token({"sub": "1"})

    parts = token.split(".")
    broken = parts[0] + "." + parts[1] + "."

    with pytest.raises(InvalidTokenError):
        decode_token(broken)

def test_jwt_invalid_algorithm():
    token = create_access_token({"sub": "1"})

    header, payload, signature = token.split(".")
    broken = f"{header}.{payload}.{signature}"

    with pytest.raises(InvalidTokenError):
        decode_token(broken, expected_type="refresh")

def test_jwt_exp_not_int():
    payload = {
        "sub": "1",
        "type": "access",
        "jti": "123",
        "exp": "not_int"
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_token(token)

def test_refresh_missing_exp(service):
    token = create_token({"sub": "1", "type": "refresh"}, timedelta(minutes=5))

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    payload.pop("exp")

    broken_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(InvalidTokenError):
        service.refresh(broken_token)

def test_get_current_user_invalid_sub(service):
    token = create_token({"sub": "not_int"}, timedelta(minutes=5))

    with pytest.raises(InvalidTokenError):
        service.get_current_user(token)

def test_decode_expired_token():
    token = create_token(
        {"sub": "1", "type": "access"},
        timedelta(seconds=-5)
    )

    with pytest.raises(InvalidTokenError):
        decode_token(token)

def test_decode_wrong_secret():
    token = jwt.encode(
        {"sub": "1", "type": "access"},
        "wrong",
        algorithm=settings.ALGORITHM
    )

    with pytest.raises(InvalidTokenError):
        decode_token(token)