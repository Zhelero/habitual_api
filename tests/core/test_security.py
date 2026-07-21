import base64
import json

from jose import jwt

from app.core.config import settings
from tests.utils.helpers import (
    random_email,
    register_user,
    get_auth_headers,
    create_habit,
)


def _make_unsigned_token(payload: dict) -> str:
    """Manually builds a raw `alg: none` JWT (header.payload.).

    python-jose's own jwt.encode() refuses to create alg=none tokens at all
    (JWSError), which is good — but it means we can't use it to test that
    our *decode* path also rejects one. This bypasses jose entirely and
    builds the token by hand, the way an attacker actually would.
    """

    def b64(obj: dict) -> str:
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = {"alg": "none", "typ": "JWT"}
    return f"{b64(header)}.{b64(payload)}."


class TestBrokenAccessControl:
    """A user must never be able to read, modify, or delete another user's data.

    The repository layer already scopes every query by user_id (see
    app/repositories/habit_repository.py), so these are regression tests —
    they lock in behavior that already exists, so a future change can't
    silently reopen this class of bug (IDOR / broken object-level auth).
    """

    def test_cannot_read_another_users_habit(self, client):
        email_a, email_b = random_email(), random_email()
        register_user(client, email_a, "12345678")
        register_user(client, email_b, "12345678")

        headers_a = get_auth_headers(client, email_a, "12345678")
        headers_b = get_auth_headers(client, email_b, "12345678")

        habit = create_habit(client, headers_a)

        response = client.get(f"/habits/{habit['id']}/", headers=headers_b)

        assert response.status_code in (403, 404)

    def test_cannot_update_another_users_habit(self, client):
        email_a, email_b = random_email(), random_email()
        register_user(client, email_a, "12345678")
        register_user(client, email_b, "12345678")

        headers_a = get_auth_headers(client, email_a, "12345678")
        headers_b = get_auth_headers(client, email_b, "12345678")

        habit = create_habit(client, headers_a)

        response = client.patch(
            f"/habits/{habit['id']}/",
            json={"name": "hijacked"},
            headers=headers_b,
        )

        assert response.status_code in (403, 404)

    def test_cannot_archive_another_users_habit(self, client):
        email_a, email_b = random_email(), random_email()
        register_user(client, email_a, "12345678")
        register_user(client, email_b, "12345678")

        headers_a = get_auth_headers(client, email_a, "12345678")
        headers_b = get_auth_headers(client, email_b, "12345678")

        habit = create_habit(client, headers_a)

        response = client.patch(f"/habits/{habit['id']}/archive/", headers=headers_b)

        assert response.status_code in (403, 404)

    def test_cannot_mark_another_users_habit_done(self, client):
        email_a, email_b = random_email(), random_email()
        register_user(client, email_a, "12345678")
        register_user(client, email_b, "12345678")

        headers_a = get_auth_headers(client, email_a, "12345678")
        headers_b = get_auth_headers(client, email_b, "12345678")

        habit = create_habit(client, headers_a)

        response = client.post(
            f"/habits/{habit['id']}/done/", headers=headers_b, json={}
        )

        assert response.status_code in (403, 404)


class TestAuthenticationRequired:
    """Every non-public endpoint must reject requests with no token,
    a malformed token, or a token that's been tampered with."""

    def test_habits_endpoint_requires_auth(self, client):
        response = client.get("/habits/")
        assert response.status_code == 401

    def test_dashboard_endpoint_requires_auth(self, client):
        response = client.get("/dashboard/")
        assert response.status_code == 401

    def test_garbage_token_is_rejected(self, client):
        response = client.get(
            "/habits/",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401

    def test_tampered_token_signature_is_rejected(self, client):
        email = random_email()
        register_user(client, email, "12345678")
        headers = get_auth_headers(client, email, "12345678")

        token = headers["Authorization"].removeprefix("Bearer ")
        # Flip a character safely inside the signature (not the last one —
        # the final base64url group of an HS256 signature only encodes 4
        # significant bits, so some replacements there don't actually change
        # the underlying bytes and the tampered token still verifies).
        sig_index = len(token) - 10
        tampered = token[:sig_index] + (
            "a" if token[sig_index] != "a" else "b" + token[sig_index + 1 :]
        )

        response = client.get(
            "/habits/", headers={"Authorization": f"Bearer {tampered}"}
        )
        assert response.status_code == 401

    def test_token_signed_with_wrong_secret_is_rejected(self, client):
        email = random_email()
        register_user(client, email, "12345678")

        # A token that's structurally valid but signed with a secret the
        # server doesn't know — simulates an attacker who guessed the
        # payload shape but not the actual secret key.
        forged = jwt.encode(
            {"sub": "1", "type": "access"},
            "not-the-real-secret",
            algorithm=settings.ALGORITHM,
        )

        response = client.get("/habits/", headers={"Authorization": f"Bearer {forged}"})
        assert response.status_code == 401

    def test_alg_none_token_is_rejected(self, client):
        # Classic JWT library bug class: some libraries historically accepted
        # alg=none tokens with no signature at all. python-jose rejects this
        # by default, but it's cheap insurance to pin the behavior in a test.
        token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0." "eyJzdWIiOiIxIn0."

        response = client.get("/habits/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


class TestInputHandling:
    """SQL injection and script-injection payloads should be stored/rejected
    safely — never executed, never break the query. SQLAlchemy's parameterized
    queries already protect against SQLi; these tests confirm that in
    practice rather than trusting the ORM blindly."""

    def test_sql_injection_payload_in_habit_name_is_stored_literally(
        self, client, auth_headers
    ):
        payload = "'; DROP TABLE habits; --"

        response = client.post("/habits/", json={"name": payload}, headers=auth_headers)

        assert response.status_code == 201
        assert response.json()["name"] == payload.lower()

        # If the payload had actually executed, this would now 500 or
        # come back empty instead of a normal, populated list.
        listing = client.get("/habits/", headers=auth_headers)
        assert listing.status_code == 200
        assert len(listing.json()["items"]) >= 1

    def test_script_payload_in_habit_name_is_stored_as_plain_text(
        self, client, auth_headers
    ):
        payload = "<script>alert('xss')</script>"

        response = client.post("/habits/", json={"name": payload}, headers=auth_headers)

        assert response.status_code == 201
        # The API's job is to store/return the raw string unmodified —
        # escaping on render is the frontend's responsibility (React does
        # this by default). What we're checking here is that the backend
        # doesn't do anything dangerous with it server-side (e.g. render
        # it into an HTML template unescaped somewhere).
        assert response.json()["name"] == payload

    def test_sql_injection_payload_in_login_email_is_rejected_safely(self, client):
        response = client.post(
            "/auth/login/",
            json={"email": "' OR '1'='1", "password": "whatever"},
        )

        # Should fail validation (not an email) or auth (no such user) —
        # either way, never a 500, and never a successful login.
        assert response.status_code in (401, 422)


class TestRateLimiting:
    """Confirms brute-force protection exists on the auth endpoints.

    Exact boundary behavior (allowed up to N, rejected on N+1) is tested in
    tests/api/test_auth.py — this just checks that hammering the endpoint
    eventually gets blocked, without duplicating the precise limits here.
    """

    def test_repeated_login_attempts_eventually_get_blocked(self, client):
        email = random_email()
        register_user(client, email, "12345678")

        statuses = [
            client.post(
                "/auth/login/",
                json={"email": email, "password": "wrong-password"},
            ).status_code
            for _ in range(10)
        ]

        assert 429 in statuses

    def test_repeated_registration_attempts_eventually_get_blocked(self, client):
        statuses = [
            client.post(
                "/auth/register/",
                json={"email": random_email(), "password": "12345678"},
            ).status_code
            for _ in range(15)
        ]

        assert 429 in statuses


class TestPasswordPolicy:
    def test_password_shorter_than_8_chars_is_rejected(self, client):
        response = client.post(
            "/auth/register/",
            json={"email": random_email(), "password": "short1"},
        )
        assert response.status_code == 422

    def test_absurdly_long_password_is_rejected(self, client):
        response = client.post(
            "/auth/register/",
            json={"email": random_email(), "password": "a" * 10_000},
        )
        assert response.status_code == 422
