import logging
from sqlalchemy.exc import IntegrityError

from app.repositories.user_repository import UserRepository
from app.db.models import User
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.core.exceptions import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserNotFoundError,
    InvalidTokenError,
)

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register(self, email: str, password: str) -> dict[str, str | int]:
        email = email.lower().strip()
        password_hash = hash_password(password)

        try:
            user = self.repo.create_user(email, password_hash)
        except IntegrityError:
            logger.warning("User already exists: %s", email)
            raise UserAlreadyExistsError()

        tokens = self._generate_tokens(user)

        return self._build_auth_response(user, tokens)

    def login(self, email: str, password: str) -> dict[str, str | int]:
        email = email.lower().strip()

        user = self.repo.get_by_email(email)

        if not user or not verify_password(password, user.password_hash):
            logger.warning("Invalid login attempt: %s", email)
            raise InvalidCredentialsError()

        tokens = self._generate_tokens(user)

        return self._build_auth_response(user, tokens)

    def refresh(self, refresh_token: str) -> dict[str, str | int]:
        try:
            payload = decode_token(refresh_token)
        except InvalidTokenError as e:
            logger.warning("Invalid refresh token: %s", str(e))
            raise InvalidCredentialsError()

        token_type = payload.get("type")
        if token_type != "refresh":
            logger.warning("Wrong token type for refresh")
            raise InvalidCredentialsError()

        user_id_str = payload.get("sub")
        if not user_id_str:
            logger.warning("Invalid credentials: missing user_id in token")
            raise InvalidCredentialsError()

        try:
            user_id = int(user_id_str)
        except ValueError:
            logger.warning("Invalid credentials: user_id is not int")
            raise InvalidCredentialsError()

        user = self.repo.get_by_id(user_id)
        if not user:
            logger.warning("User not found during refresh")
            raise UserNotFoundError()

        tokens = self._generate_tokens(user)

        return self._build_auth_response(user, tokens)

    def get_current_user(self, user_id: int) -> User:
        user = self.repo.get_by_id(user_id)
        if not user:
            logger.warning("User not found: %s", user_id)
            raise UserNotFoundError()
        return user


    # HELPERS

    def _generate_tokens(self, user: User) -> dict[str, str]:
        payload = self._build_token_payload(user)
        return {
            "access_token": create_access_token(payload),
            "refresh_token": create_refresh_token(payload)
        }

    def _build_auth_response(self, user: User, tokens: dict[str, str]) -> dict[str, str | int]:
        return {
            **tokens,
            "token_type": "bearer",
            "user_id": user.id
        }

    def _build_token_payload(self, user: User) -> dict[str, str]:
        return {
            "sub": str(user.id),
            "email": user.email,
        }