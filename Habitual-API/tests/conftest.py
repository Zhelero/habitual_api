import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.deps import get_db

SQLALCHEMY_DATABASE_URI = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db():
    connection = engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()

        if transaction.is_active:
            transaction.rollback()

        connection.close()

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)

@pytest.fixture
def user_token(client):
    import uuid

    email = f"{uuid.uuid4()}@test.com"
    password = "123456"

    client.post("/auth/register/", json={
        "email": email,
        "password": password
    })

    response = client.post("/auth/login/", json={
        "email": email,
        "password": password
    })

    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}

@pytest.fixture
def mock_session(mocker):
    mock = mocker.Mock()
    mocker.patch("app.db.session.SessionLocal", return_value=mock)
    return mock