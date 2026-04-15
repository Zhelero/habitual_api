from datetime import datetime, timezone, timedelta

import pytest

from tests.utils.helpers import random_email, register_user, get_auth_headers

DEFAULT_PASSWORD = "123456"


class TestRegister:

    def test_register_success(self, client):
        email = random_email()

        data = register_user(client, email, DEFAULT_PASSWORD)

        assert isinstance(data["user_id"], int)
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert data["token_type"] == "bearer"

    def test_register_email_normalized(self, client):
        email = "TEST@TEST.COM"

        data = register_user(client, email, DEFAULT_PASSWORD)

        me = client.get(
            "/auth/me/", headers={"Authorization": f"Bearer {data['access_token']}"}
        )
        assert me.json()["email"] == email.lower()

    def test_register_duplicate(self, client):
        email = random_email()
        payload = {"email": email, "password": DEFAULT_PASSWORD}
        client.post("/auth/register/", json=payload)
        response = client.post("/auth/register/", json=payload)

        assert response.status_code == 409

    def test_register_empty_email(self, client):
        response = client.post(
            "/auth/register/", json={"email": "", "password": DEFAULT_PASSWORD}
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("password", ["", "123", " "])
    def test_register_invalid_password(self, client, password):
        response = client.post(
            "/auth/register/", json={"email": random_email(), "password": password}
        )

        assert response.status_code == 422

    def test_register_short_password(self, client):
        response = client.post(
            "/auth/register/", json={"email": random_email(), "password": "12345"}
        )

        assert response.status_code == 422

    def test_many_users(self, client):
        for _ in range(10):
            register_user(client, random_email(), DEFAULT_PASSWORD)


class TestLogin:
    def test_login(self, client):
        email = random_email()
        register_user(client, email, DEFAULT_PASSWORD)

        response = client.post(
            "/auth/login/", json={"email": email, "password": DEFAULT_PASSWORD}
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["user_id"], int)
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        email = random_email()

        register_user(client, email, DEFAULT_PASSWORD)

        response = client.post(
            "/auth/login/", json={"email": email, "password": "wrong123"}
        )

        assert response.status_code == 401

    def test_login_invalid_credentials(self, client):
        response = client.post(
            "/auth/login/", json={"email": random_email(), "password": DEFAULT_PASSWORD}
        )

        assert response.status_code == 401

    def test_login_expired_token(self, client, freeze_time):
        email = random_email()
        now = datetime.now(timezone.utc)

        register_user(client, email, DEFAULT_PASSWORD)
        with freeze_time(now - timedelta(minutes=32)):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            response = client.get("/auth/me/", headers=auth_headers)

            assert response.status_code == 200

        with freeze_time(now):
            response = client.get("/auth/me/", headers=auth_headers)
            assert response.status_code == 401


class TestMe:
    def test_me(self, client, auth_headers):
        response = client.get("/auth/me/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["id"], int)
        assert "@" in data["email"]

    def test_me_without_token(self, client):
        response = client.get("/auth/me/")

        assert response.status_code == 401

    def test_me_with_invalid_token(self, client):
        response = client.get(
            "/auth/me/", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    def test_user_id_consistency(self, client):
        user = register_user(client)

        user_id = user["user_id"]
        token = user["access_token"]

        me = client.get("/auth/me/", headers={"Authorization": f"Bearer {token}"})

        assert me.json()["id"] == user_id


class TestRefresh:
    def test_refresh_success(self, client):
        user = register_user(client)
        old_refresh = user["refresh_token"]

        response2 = client.post("/auth/refresh/", json={"refresh_token": old_refresh})

        new_refresh = response2.json()["refresh_token"]

        assert response2.status_code == 200

        assert old_refresh != new_refresh

        data = response2.json()

        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert data["token_type"] == "bearer"
        assert data["user_id"] == user["user_id"]
        assert data["access_token"] != user["access_token"]

    def test_refresh_chain(self, client):
        user = register_user(client)

        refresh_token = user["refresh_token"]

        # first refresh
        res2 = client.post("/auth/refresh/", json={"refresh_token": refresh_token})

        assert res2.status_code == 200
        new_refresh = res2.json()["refresh_token"]

        # second refresh with new token
        res3 = client.post("/auth/refresh/", json={"refresh_token": new_refresh})

        assert res3.status_code == 200

    def test_refresh_token_rotation(self, client):
        user = register_user(client)
        refresh_token = user["refresh_token"]

        client.post("/auth/refresh/", json={"refresh_token": refresh_token})

        response = client.post("/auth/refresh/", json={"refresh_token": refresh_token})

        assert response.status_code == 401

    def test_refresh_invalid_token(self, client):
        res = client.post(
            "/auth/refresh/",
            json={
                "refresh_token": "invalid_token",
            },
        )

        assert res.status_code == 401

    def test_refresh_with_access_token(self, client):
        user = register_user(client)

        response = client.post(
            "/auth/refresh/", json={"refresh_token": user["access_token"]}
        )

        assert response.status_code == 401

    def test_refresh_expired_token(self, client, freeze_time):
        email = random_email()
        now = datetime.now(timezone.utc)

        register_user(client, email, DEFAULT_PASSWORD)
        with freeze_time(now - timedelta(days=8)):
            response = client.post(
                "/auth/login/", json={"email": email, "password": DEFAULT_PASSWORD}
            )

            refresh_token = response.json()["refresh_token"]
            assert response.status_code == 200

        with freeze_time(now):
            response = client.post(
                "/auth/refresh/", json={"refresh_token": refresh_token}
            )

        assert response.status_code == 401

    def test_refresh_after_logout(self, client):
        user = register_user(client)

        client.post(
            "/auth/logout/", headers={"Authorization": f"Bearer {user['access_token']}"}
        )

        response = client.post(
            "/auth/refresh/", json={"refresh_token": user["refresh_token"]}
        )

        assert response.status_code in (200, 401)


class TestLogout:
    def test_logout(self, client, auth_headers):
        response = client.post("/auth/logout/", headers=auth_headers)

        assert response.status_code == 204

    def test_access_after_logout(self, client, auth_headers):
        client.post("/auth/logout/", headers=auth_headers)

        response = client.get("/auth/me/", headers=auth_headers)

        assert response.status_code == 401

    def test_logout_twice(self, client, auth_headers):
        client.post("/auth/logout/", headers=auth_headers)

        response = client.post("/auth/logout/", headers=auth_headers)

        assert response.status_code in (204, 401)

    def test_logout_invalid_token(self, client):
        response = client.post(
            "/auth/logout/", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code in (204, 401)

    def test_logout_empty_token(self, client):
        response = client.post("/auth/logout/", headers={})

        assert response.status_code == 204
