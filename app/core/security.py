from passlib.context import CryptContext
from passlib.exc import UnknownHashError

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if not isinstance(password, str):
        return False

    try:
        return pwd_context.verify(password, hashed)
    except (UnknownHashError, ValueError):
        return False
