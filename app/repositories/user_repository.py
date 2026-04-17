import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import User

logger = logging.getLogger("app.users")


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        user = self.db.execute(stmt).scalar_one_or_none()

        logger.debug("Get user by email email=%s found=%s", email, bool(user))

        return user

    def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        user = self.db.execute(stmt).scalar_one_or_none()

        logger.debug(
            "Get user by id user_id=%s found=%s",
            user_id,
            bool(user),
        )

        return user

    def create_user(self, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)

        logger.info(
            "User created user_id=%s email=%s",
            user.id,
            user.email,
        )

        return user
