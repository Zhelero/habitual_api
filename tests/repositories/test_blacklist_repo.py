from datetime import datetime, timedelta, timezone

from app.repositories.blacklist_repository import TokenBlacklistRepository


def test_add_token(db):
    repo = TokenBlacklistRepository(db)
    token = repo.add("jti1", datetime.now())
    assert token is not None


def test_is_blacklisted(db):
    repo = TokenBlacklistRepository(db)
    repo.add("jti1", datetime.now())
    assert repo.is_blacklisted("jti1") is True


def test_delete_expired_tokens(db):
    repo = TokenBlacklistRepository(db)

    now = datetime.now(timezone.utc)

    repo.add("old", now - timedelta(days=1))
    repo.add("valid", now + timedelta(days=1))

    deleted = repo.delete_expired_tokens(now)

    assert deleted == 1
    assert repo.is_blacklisted("old") is False
    assert repo.is_blacklisted("valid") is True


def test_blacklist_duplicate(db):
    repo = TokenBlacklistRepository(db)
    jti = "abc"
    exp = datetime.now(timezone.utc)

    repo.add(jti, exp)
    repo.add(jti, exp)

    assert repo.is_blacklisted(jti) is False


def test_blacklist_unknown_token(db):
    repo = TokenBlacklistRepository(db)

    assert repo.is_blacklisted("unknown") is False
