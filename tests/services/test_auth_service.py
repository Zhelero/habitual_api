from datetime import timezone, datetime

import pytest

from jose import jwt

from app.core.config import settings
from app.core.jwt import decode_token, create_access_token
from app.core.exceptions import InvalidCredentialsError, TokenRevokedError, UserAlreadyExistsError, InvalidTokenError, \
    UserNotFoundError
from tests.utils.helpers import random_email

DEFAULT_PASSWORD = "123456"

class TestRegister:
    def test_register_success(self, service):
        data = service.register("test@test.com", DEFAULT_PASSWORD)

        assert isinstance(data["user_id"], int)
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert data["token_type"] == "bearer"

    def test_register_email_normalized(self, service):
        data = service.register("TEST@TEST.COM", DEFAULT_PASSWORD)

        decoded = decode_token(data["access_token"])
        assert decoded["email"] == "test@test.com"

    def test_register_empty_name(self, service):
        with pytest.raises(InvalidCredentialsError):
            service.register("", DEFAULT_PASSWORD)

    def test_register_trim_email(self, service):
        data = service.register("    test@test.com      ", DEFAULT_PASSWORD)

        decoded = decode_token(data["access_token"])
        assert decoded["email"] == "test@test.com"

    def test_register_empty_password(self, service):
        with pytest.raises(InvalidCredentialsError):
            service.register("test@test.com", "")

    def test_register_short_password(self, service):
        with pytest.raises(InvalidCredentialsError):
            service.register("test@test.com", "123")

    def test_register_duplicate_email(self, service):
        email = random_email()
        service.register(email, DEFAULT_PASSWORD)

        with pytest.raises(UserAlreadyExistsError):
            service.register(email, DEFAULT_PASSWORD)


class TestLogin:
    def test_login_success(self, service):
        email = random_email()
        service.register(email, DEFAULT_PASSWORD)
        tokens = service.login(email, DEFAULT_PASSWORD)

        assert "access_token" in tokens
        assert "refresh_token" in tokens

    def test_login_email_normalized(self, service):
        service.register("test@test.com", DEFAULT_PASSWORD)
        data = service.login("TEST@TEST.COM", DEFAULT_PASSWORD)

        decoded = decode_token(data["access_token"])
        assert decoded["email"] == "test@test.com"

    def test_login_raises_when_user_not_found(self, service):
        with pytest.raises(InvalidCredentialsError):
            service.login("no@user.com", DEFAULT_PASSWORD)

    def test_login_wrong_password(self, service):
        email = random_email()
        service.register(email, DEFAULT_PASSWORD)

        with pytest.raises(InvalidCredentialsError):
            service.login(email, "wrong123")


class TestRefreshToken:
    def test_refresh_success(self, service):
        tokens = _create_user_and_login(service)
        refresh_token = tokens["refresh_token"]
        access_token = tokens["access_token"]

        new_tokens = service.refresh(refresh_token)

        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

        assert isinstance(new_tokens["access_token"], str)
        assert isinstance(new_tokens["refresh_token"], str)

        assert new_tokens["refresh_token"] != refresh_token
        assert new_tokens["access_token"] != access_token

        decoded = decode_token(new_tokens["access_token"])
        assert int(decoded["sub"]) > 0

    def test_refresh_rotates_and_invalidates_old_token(self, service):
        tokens = _create_user_and_login(service)
        old_refresh_token = tokens["refresh_token"]

        rotation_tokens = service.refresh(old_refresh_token)
        new_refresh_token = rotation_tokens["refresh_token"]

        result = service.refresh(new_refresh_token)
        assert "access_token" in result
        assert "refresh_token" in result

        with pytest.raises(TokenRevokedError):
            service.refresh(old_refresh_token)

    def test_refresh_invalid_token(self, service):
        with pytest.raises(InvalidTokenError):
            service.refresh("invalid_token")

    def test_refresh_access_token(self, service):
        tokens = _create_user_and_login(service)

        with pytest.raises(InvalidTokenError):
            service.refresh(tokens["access_token"])

    def test_refresh_user_not_found(self, service):
        tokens = _create_user_and_login(service)

        payload = decode_token(tokens["refresh_token"])
        payload["sub"] = "999999"

        broken = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        with pytest.raises(UserNotFoundError):
            service.refresh(broken)

    def test_refresh_after_logout(self, service):
        tokens = _create_user_and_login(service)
        refresh = tokens["refresh_token"]

        service.logout(refresh)

        with pytest.raises(TokenRevokedError):
            service.refresh(refresh)

    def test_refresh_generates_new_jti(self, service):
        tokens = _create_user_and_login(service)

        first = decode_token(tokens["refresh_token"])

        new = service.refresh(tokens["refresh_token"])
        second = decode_token(new["refresh_token"])

        assert first["jti"] != second["jti"]

    def test_refresh_missing_jti(self, service):
        tokens = _create_user_and_login(service)

        payload = decode_token(tokens["refresh_token"])
        payload.pop("jti")

        broken = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        with pytest.raises(InvalidTokenError):
            service.refresh(broken)

    def test_refresh_missing_exp(self, service):
        tokens = _create_user_and_login(service)

        payload = decode_token(tokens["refresh_token"])
        payload.pop("exp")

        broken = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        with pytest.raises(InvalidTokenError):
            service.refresh(broken)

    def test_refresh_exp_datetime(self, service):
        tokens = _create_user_and_login(service)

        payload = decode_token(tokens["refresh_token"])
        payload["exp"] = datetime.now(timezone.utc)

        broken = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        service.refresh(broken)

    def test_refresh_invalid_exp_format(self, service):
        tokens = _create_user_and_login(service)

        payload = decode_token(tokens["refresh_token"])
        payload["exp"] = "invalid"

        broken = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        with pytest.raises(InvalidTokenError):
            service.refresh(broken)

    def test_refresh_blacklist_old_token(self, service):
        tokens = _create_user_and_login(service)

        payload = decode_token(tokens["refresh_token"])
        jti = payload["jti"]

        service.refresh(tokens["refresh_token"])

        assert service.blacklist_repo.is_blacklisted(jti)


class TestMe:
    def test_me_success(self, service):
        tokens = _create_user_and_login(service)

        user = service.get_current_user(tokens["access_token"])
        assert user.id == tokens["user_id"]
        assert "@" in user.email

    def test_me_revoked_token(self, service):
        tokens = _create_user_and_login(service)

        service.logout(tokens["access_token"])

        with pytest.raises(TokenRevokedError):
            service.get_current_user(tokens["access_token"])

    def test_me_invalid_token(self, service):
        with pytest.raises(InvalidTokenError):
            service.get_current_user("")


class TestLogout:
    def test_logout_revokes_token(self, service):
        tokens = _create_user_and_login(service)
        access_token = tokens["access_token"]

        service.logout(access_token)

        with pytest.raises(TokenRevokedError):
            decode_token(access_token, blacklist_repo=service.blacklist_repo)

    def test_logout_and_login_success(self, service):
        email = random_email()

        service.register(email, DEFAULT_PASSWORD)
        tokens = service.login(email, DEFAULT_PASSWORD)

        service.logout(tokens["access_token"])

        new = service.login(email, DEFAULT_PASSWORD)

        assert new["access_token"] != tokens["access_token"]

    def test_logout_and_refresh_token(self, service):
        tokens = _create_user_and_login(service)

        service.logout(tokens["refresh_token"])

        with pytest.raises(TokenRevokedError):
            service.refresh(tokens["refresh_token"])

    def test_logout_does_not_crash_on_invalid_token(self, service):
        service.logout("invalid_token")

    def test_logout_missing_jti(self, service):
        token = create_access_token({"sub": "1"})
        payload = decode_token(token)

        payload.pop("jti")

        broken = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        #logout should be idempotent and not crash
        service.logout(broken)

    def test_logout_missing_exp(self, service):
        token = create_access_token({"sub": "1"})
        payload = decode_token(token)

        payload.pop("exp")

        broken = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        service.logout(broken)

    def test_logout_twice(self, service):
        tokens = _create_user_and_login(service)
        access = tokens["access_token"]

        service.logout(access)
        service.logout(access)

    def test_logout_invalid_refresh_token(self, service):
        service.logout("invalid_refresh_token")

#HELPER

def _create_user_and_login(service):
    email = random_email()
    service.register(email, DEFAULT_PASSWORD)

    return service.login(email, DEFAULT_PASSWORD)
