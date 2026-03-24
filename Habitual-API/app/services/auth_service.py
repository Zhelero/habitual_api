import logging
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from app.repositories.blacklist_repository import TokenBlacklistRepository
from app.repositories.user_repository import UserRepository
from app.db.models import User
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.core.exceptions import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserNotFoundError,
    InvalidTokenError,
    TokenRevokedError,
)

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(
            self,
            repo: UserRepository,
            blacklist_repo: TokenBlacklistRepository
    ):
        self.repo = repo
        self.blacklist_repo = blacklist_repo

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
            logger.warning("Invalid login attempt", extra={"email": email})
            raise InvalidCredentialsError()

        tokens = self._generate_tokens(user)

        return self._build_auth_response(user, tokens)

    def refresh(self, refresh_token: str) -> dict[str, str | int]:
        payload = decode_token(
            refresh_token,
            expected_type="refresh",
            blacklist_repo=self.blacklist_repo
        )

        user_id = int(payload["sub"])
        user = self.repo.get_by_id(user_id)

        if not user:
            logger.warning("User not found during refresh")
            raise UserNotFoundError()

        jti = payload.get("jti")
        if not jti:
            logger.warning("Refresh: missing jti")
            raise InvalidTokenError("Missing jti")

        expires_at = self._get_expires_at(payload)

        self.blacklist_repo.add(jti, expires_at)

        tokens = self._generate_tokens(user)

        return self._build_auth_response(user, tokens)

    def get_current_user(self, token: str) -> User:
        payload = decode_token(
            token,
            expected_type="access",
            blacklist_repo=self.blacklist_repo
        )

        try:
            user_id = int(payload["sub"])
        except (KeyError, ValueError):
            raise InvalidTokenError("Invalid subject")

        user = self.repo.get_by_id(user_id)

        if not user:
            raise UserNotFoundError()

        return user

    def logout(self, token: str):
        try:
            payload = decode_token(
                token,
                expected_type="access",
                blacklist_repo=None)
        except InvalidTokenError:
            logger.warning("Logout with invalid token")
            return

        jti = payload.get("jti")
        if not jti:
            logger.warning("Logout: missing jti")
            return

        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        self.blacklist_repo.add(jti, expires_at)


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

    def _get_expires_at(self, payload: dict) -> datetime:
        exp = payload.get("exp")
        if not exp:
            raise InvalidTokenError("Missing exp")

        if isinstance(exp, int):
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return exp