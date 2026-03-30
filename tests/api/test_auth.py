import uuid
import pytest

from app.core.security import verify_password, hash_password
from app.core.jwt import decode_token, create_access_token, create_token
from app.core.exceptions import InvalidTokenError, TokenRevokedError
from app.services.helpers import normalize_str
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.repositories.blacklist_repository import TokenBlacklistRepository


# Positive cases

def test_register(client):
    response = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456"
    })

    assert response.status_code == 201
    data = response.json()

    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)
    assert data["token_type"] == "bearer"
    assert isinstance(data["user_id"], int)

def test_login(client):
    email = random_email()
    client.post("/auth/register/", json={
        "email": email,
        "password": "123456"
    })

    response = client.post("/auth/login/", json={
        "email": email,
        "password": "123456"
    })

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)

def test_me(client, auth_headers):
    response = client.get("/auth/me/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["id"], int)
    assert "@" in data["email"]


def test_refresh_token(client):
    res = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456"
    })
    old_refresh = res.json()["refresh_token"]

    response2 = client.post("/auth/refresh/", json={
        "refresh_token": old_refresh
    })

    new_refresh = response2.json()["refresh_token"]

    assert response2.status_code == 200

    assert old_refresh != new_refresh

    data = response2.json()

    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)
    assert data["token_type"] == "bearer"

def test_refresh_chain(client):
    res = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456"
    })

    refresh_token = res.json()["refresh_token"]

    #first refresh
    res2 = client.post("/auth/refresh/", json={
        "refresh_token": refresh_token
    })

    assert res2.status_code == 200
    new_refresh = res2.json()["refresh_token"]

    # second refresh with new token
    res3 = client.post("/auth/refresh/", json={
        "refresh_token": new_refresh
    })

    assert res3.status_code == 200

def test_logout(client, auth_headers):
    response = client.post("/auth/logout/", headers=auth_headers)

    assert response.status_code == 204

def test_verify_password_true():
    password = "123456"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True

def test_get_db():
    from app.db.deps import get_db

    gen = get_db()
    db = next(gen)

    assert db is not None

    try:
        next(gen)
    except StopIteration:
        pass

def test_session_creation():
    from app.db.session import SessionLocal

    session = SessionLocal()
    assert session is not None
    session.close()


# Negative cases

def test_register_duplicate(client):
    email = random_email()
    payload = {
        "email": email,
        "password": "123456"
    }
    client.post("/auth/register/", json=payload)
    response = client.post("/auth/register/", json=payload)

    assert response.status_code == 409

def test_register_empty_email(client):
    response = client.post("/auth/register/", json={
        "email": "",
        "password": "123456"
    })

    assert response.status_code == 422

def test_login_user_not_found(db):

    service = build_service(db)

    with pytest.raises(Exception):
        service.login("no@user.com", "123456")

def test_login_wrong_password(client):
    email = random_email()

    client.post("/auth/register/", json={
        "email": email,
        "password": "123456"
    })

    response = client.post("/auth/login/", json={
        "email": email,
        "password": "wrong123"
    })

    assert response.status_code == 401

def test_login_wrong_password_service(db):

    service = build_service(db)

    email = "test@test.com"
    service.register(email, "123456")

    with pytest.raises(Exception):
        service.login(email, "wrong123")

def test_login_invalid_credentials(client):
    response = client.post("/auth/login/", json={
        "email": random_email(),
        "password": "123456"
    })

    assert response.status_code == 401

def test_refresh_token_rotation(client):
    res = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456"
    })
    refresh_token = res.json()["refresh_token"]

    client.post("/auth/refresh/", json={
        "refresh_token": refresh_token
    })

    response = client.post("/auth/refresh/", json={
        "refresh_token": refresh_token
    })

    assert response.status_code == 401

def test_refresh_invalid_token(client):
    res = client.post("/auth/refresh/", json={
        "refresh_token": "invalid_token",
    })

    assert res.status_code == 401

def test_refresh_missing_exp(db):
    from datetime import timedelta

    service = build_service(db)

    token = create_token({"sub": "1", "type": "refresh"}, timedelta(minutes=5))

    from jose import jwt
    from app.core.config import settings

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    payload.pop("exp")

    broken_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(InvalidTokenError):
        service.refresh(broken_token)

def test_get_current_user_invalid_sub(db):
    from datetime import timedelta

    service = build_service(db)

    token = create_token({"sub": "not_int"}, timedelta(minutes=5))

    with pytest.raises(InvalidTokenError):
        service.get_current_user(token)

def test_access_after_logout(client, auth_headers):
    client.post("/auth/logout/", headers=auth_headers)

    response = client.get("/auth/me/", headers=auth_headers)

    assert response.status_code == 401

def test_logout_twice(client, auth_headers):
    client.post("/auth/logout/", headers=auth_headers)

    response = client.post("/auth/logout/", headers=auth_headers)

    assert response.status_code in (204, 401)

def test_logout_invalid_token(client):
    response = client.post("/auth/logout/", headers={
        "Authorization": "Bearer invalid_token"
    })

    assert response.status_code in (204, 401)

def test_logout_invalid_token_no_crash(db):
    service = build_service(db)

    service.logout("invalid_token")

def test_logout_missing_jti(db):
    service = build_service(db)

    token = create_access_token({"sub": "1"})
    payload = decode_token(token)

    payload.pop("jti")

    service.logout(token)

def test_me_without_token(client):
    response = client.get("/auth/me/")

    assert response.status_code == 401

def test_blacklisted_token_access(client, auth_headers):
    client.post("/auth/logout/", headers=auth_headers)

    response = client.get("/auth/me/", headers=auth_headers)

    assert response.status_code == 401

def test_blacklist_token_flow(client):
    res = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456"
    })
    token = res.json()["access_token"]

    client.post("/auth/logout/", headers={
        "Authorization": f"Bearer {token}"
    })

    res = client.get("/auth/me/", headers={
        "Authorization": f"Bearer {token}"
    })

    assert res.status_code == 401

def test_access_with_invalid_token(client):
    response = client.get("/auth/me/", headers={
        "Authorization": "Bearer invalid_token"
    })

    assert response.status_code == 401

def test_verify_password_false():
    hashed = hash_password("123456")

    assert verify_password("wrong_password", hashed) is False

def test_hash_password_not_equal_plain():
    password = "123456"
    hashed = hash_password(password)

    assert hashed != password

def test_hash_password_changes():
    from app.core.security import hash_password

    p1 = hash_password("123456")
    p2 = hash_password("123456")

    assert p1 != p2

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

# Parametrized tests

def test_db_session_works(client):
    res = client.get("/habits/")
    assert res.status_code in (200, 401)

@pytest.mark.parametrize("password", ["", "123", " "])
def test_register_invalid_password(client, password):
    response = client.post("/auth/register/", json={
        "email": random_email(),
        "password": password
    })

    assert response.status_code == 422

def test_user_id_consistency(client):
    res = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456"
    })

    user_id = res.json()["user_id"]
    token = res.json()["access_token"]

    me = client.get("/auth/me/", headers={
        "Authorization": f"Bearer {token}"
    })

    assert me.json()["id"] == user_id

def test_many_users(client):
    for _ in range(10):
        response = client.post("/auth/register/", json={
            "email": random_email(),
            "password": "123456"
        })
        assert response.status_code == 201

def test_normalize_str():
    assert normalize_str("  teSt    ") == "test"
    assert normalize_str("TEst  ") == "test"
    assert normalize_str("  ") is None
    assert normalize_str(None) is None


# HELPER

def random_email():
    return f"{uuid.uuid4()}@test.com"

def build_service(db):
    return AuthService(UserRepository(db), TokenBlacklistRepository(db))