import hashlib
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)

def _normalize_password(password: str) -> bytes:
    return hashlib.sha256(password.encode()).digest()

def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))

def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(_normalize_password(password), hashed)
    except UnknownHashError:
        return False