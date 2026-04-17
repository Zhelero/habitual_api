import pytest
from passlib.exc import UnknownHashError

from app.core.security import verify_password, hash_password, pwd_context


def test_verify_password_true():
    password = "123456"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True


def test_verify_password_false():
    hashed = hash_password("123456")

    assert verify_password("wrong_password", hashed) is False


def test_verify_password_empty():
    hashed = hash_password("123456")

    assert verify_password("", hashed) is False


def test_verify_with_invalid_hash():
    result = verify_password("123456", "invalid_hash")

    assert result is False


def test_verify_does_not_modify_hash():
    password = "123456"
    hashed = hash_password(password)

    verify_password(password, hashed)

    assert isinstance(hashed, str)


def test_verify_password_unknown_hash(mocker):
    mocker.patch.object(pwd_context, "verify", side_effect=UnknownHashError())

    result = verify_password("123456", "some_hash")
    assert result is False


def test_verify_password_value_error(mocker):
    mocker.patch.object(pwd_context, "verify", side_effect=ValueError("bad"))

    result = verify_password("123456", "some_hash")
    assert result is False


def test_verify_password_unexpected_error(mocker):
    mocker.patch.object(pwd_context, "verify", side_effect=RuntimeError("boom"))

    result = verify_password("123456", "some_hash")
    assert result is False


def test_hash_password_not_equal_plain():
    password = "123456"
    hashed = hash_password(password)

    assert hashed != password


@pytest.mark.parametrize("password", [None, 123, [], {}])
def test_verify_password_invalid_types(password):
    result = verify_password(password, "hash")

    assert result is False


def test_hash_password_unexpected_error(mocker):
    mocker.patch.object(pwd_context, "hash", side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        hash_password("123456")


def test_hash_password_changes():
    p1 = hash_password("123456")
    p2 = hash_password("123456")

    assert p1 != p2


def test_hash_empty_password():
    hashed = hash_password("")
    assert isinstance(hashed, str)
    assert hashed != ""


@pytest.mark.parametrize("password", [None, 123, [], {}])
def test_hash_invalid_types(password):
    with pytest.raises(TypeError):
        hash_password(password)
