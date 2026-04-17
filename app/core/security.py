import logging
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    if not isinstance(password, str):
        logger.error("hash_password: password is not string")
        raise TypeError("Password must be a string")

    try:
        return pwd_context.hash(password)
    except Exception:
        logger.exception("hash_password failed")
        raise


def verify_password(password: str, hashed: str) -> bool:
    if not isinstance(password, str):
        logger.debug("verify_password: password is not string")
        return False

    try:
        return pwd_context.verify(password, hashed)

    except UnknownHashError:
        logger.error("verify_password: unknown hash format")
        return False

    except ValueError:
        logger.error("verify_password: invalid hash value")
        return False

    except Exception:
        logger.exception("verify_password: unknown error")
        return False
