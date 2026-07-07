import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from freezegun import freeze_time as _freeze_time
from datetime import datetime

from app.core.config import settings
from app.core.jwt import create_access_token
from app.core.rate_limit import limiter
from app.main import app
from app.db.base import Base
from app.db.deps import get_db
from tests.utils.helpers import build_service
from tests.factories.user_factory import UserFactory
from tests.factories.habit_factory import HabitFactory
from tests.factories.log_factory import HabitLogFactory

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
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


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    # slowapi's counters live in process memory, keyed by client IP + route,
    # and are NOT reset between tests the way the DB is. Every test that
    # calls register/login through TestClient shares the same fake client IP
    # ("testclient"), so without this, rate-limit state would accumulate
    # across the whole suite — and the two tests that deliberately trip the
    # limit (TestRateLimiting) would poison every test that runs afterward.
    limiter.reset()
    yield


@pytest.fixture(scope="function")
def db():
    connection = engine.connect()
    transaction = connection.begin()

    # join_transaction_mode="create_savepoint" wraps the session in a SAVEPOINT.
    # Application code calling db.commit()/db.rollback() (e.g. the `user`/`habit`
    # fixtures, or TokenBlacklistRepository.add() on IntegrityError) only ends
    # that SAVEPOINT — SQLAlchemy transparently opens a new one right after —
    # so the outer `transaction` below still rolls back everything at teardown.
    # Without this, a commit() inside a test permanently writes to the real DB
    # and leaks into every test that runs afterwards.
    session = TestingSessionLocal(
        bind=connection, join_transaction_mode="create_savepoint"
    )

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
def mock_session(mocker):
    mock = mocker.Mock()
    mocker.patch("app.db.session.SessionLocal", return_value=mock)
    return mock


@pytest.fixture
def service(db):
    return build_service(db)


@pytest.fixture
def freeze_time():
    def _freeze(dt: datetime | str):
        return _freeze_time(dt)

    return _freeze


@pytest.fixture
def base_time():
    return datetime(2026, 2, 1)


@pytest.fixture(autouse=True)
def setup_factories(db):
    for factory_cls in (UserFactory, HabitFactory, HabitLogFactory):
        factory_cls._meta.sqlalchemy_session = db


@pytest.fixture
def auth_headers(user):
    token = create_access_token({"sub": str(user.id)})

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture
def auth_tokens(service, user):
    return service.login(user.email, "12345678")


@pytest.fixture
def user(db):
    user = UserFactory()
    db.commit()
    return user


@pytest.fixture
def habit(user, db):
    habit = HabitFactory(user=user)
    db.commit()
    return habit
