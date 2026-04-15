import pytest

from app.db.deps import get_db


def test_get_db_commit(mocker):
    mock_session = mocker.MagicMock()
    mocker.patch("app.db.deps.SessionLocal", return_value=mock_session)

    gen = get_db()
    next(gen)

    with pytest.raises(StopIteration):
        next(gen)

    mock_session.commit.assert_called_once()


def test_get_db_rollback(mocker):
    mock_session = mocker.MagicMock()
    mocker.patch("app.db.deps.SessionLocal", return_value=mock_session)

    gen = get_db()
    next(gen)

    with pytest.raises(ValueError):
        gen.throw(ValueError())

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()


def test_session_creation():
    from app.db.session import SessionLocal

    session = SessionLocal()
    assert session is not None
    session.close()


def test_db_session_works(client):
    res = client.get("/habits/")
    assert res.status_code in (200, 401)


def test_get_db_close(mocker):
    mock_session = mocker.MagicMock()
    mocker.patch("app.db.deps.SessionLocal", return_value=mock_session)

    gen = get_db()
    next(gen)

    with pytest.raises(StopIteration):
        next(gen)

    mock_session.close.assert_called_once()
