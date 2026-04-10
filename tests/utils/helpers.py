import uuid

from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.repositories.blacklist_repository import TokenBlacklistRepository


def random_habit_name():
    return f"habit {uuid.uuid4()}"

def random_email():
    return f"{uuid.uuid4()}@test.com"

def build_service(db):
    return AuthService(UserRepository(db), TokenBlacklistRepository(db))

def create_habit(client, headers, name=None):
    res = client.post("/habits/", json={
        "name": name or random_habit_name(),
    }, headers=headers)

    assert res.status_code == 201
    return res.json()

def register_user(client, email = None, password=None):
    email = email or random_email()
    password = password or "123456"

    response = client.post("/auth/register/", json={
        "email": email,
        "password": password,
    })
    assert response.status_code == 201
    return response.json()

def get_auth_headers(client, email, password):
    response = client.post("/auth/login/", json={
        "email": email,
        "password": password,
    })
    assert response.status_code == 200, response.json()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}