import pytest

from app.core.security import verify_password, hash_password


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


def test_hash_password_not_equal_plain():
    password = "123456"
    hashed = hash_password(password)

    assert hashed != password


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
