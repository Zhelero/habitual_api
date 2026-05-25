import pytest

from app.core.jwt import create_access_token
from tests.factories.habit_factory import HabitFactory
from tests.factories.user_factory import UserFactory
from tests.services.test_auth_service import DEFAULT_PASSWORD
from tests.utils.helpers import (
    create_habit,
    random_habit_name,
    register_user,
    get_auth_headers,
    random_email,
)
from datetime import timedelta, date


class TestCreateHabit:
    def test_create_habit(self, client, auth_headers):
        name = random_habit_name()
        response = client.post(
            "/habits/",
            json={"name": name, "description": "Test habit"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert isinstance(data["id"], int)
        assert data["name"] == name
        assert data["description"] == "Test habit"

    def test_create_habit_empty_name(self, client, auth_headers):
        response = client.post("/habits/", json={"name": ""}, headers=auth_headers)

        assert response.status_code == 422

    def test_create_blank_name(self, client, auth_headers):
        response = client.post(
            "/habits/",
            json={
                "name": "      ",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_create_habit_long_name(self, client, auth_headers):
        response = client.post(
            "/habits/", json={"name": "a" * 260}, headers=auth_headers
        )

        assert response.status_code == 422

    def test_create_habit_duplicate_name(self, client, auth_headers, user):
        name = random_habit_name()

        HabitFactory(
            user=user,
            name=name,
        )

        response = client.post("/habits/", json={"name": name}, headers=auth_headers)

        assert response.status_code == 409

    def test_create_habit_invalid_token(self, client):
        response = client.post(
            "/habits/",
            json={"name": random_habit_name()},
            headers={"Authorization": "Bearer wrong_token"},
        )

        assert response.status_code == 401

    def test_create_habit_without_token(self, client):
        response = client.post(
            "/habits/",
            json={"name": random_habit_name()},
        )

        assert response.status_code == 401


class TestGetHabits:
    def test_get_habits(self, client, user, auth_headers):
        HabitFactory.create_batch(5, user=user)

        response = client.get("/habits/?limit=2&offset=0", headers=auth_headers)

        assert response.status_code == 200

        data = response.json()

        assert len(data["items"]) == 2
        assert data["total"] == 5

        item = data["items"][0]
        assert "id" in item
        assert "name" in item

    def test_get_habit_by_id(self, client, auth_headers, habit):
        response = client.get(f"/habits/{habit.id}/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == habit.id
        assert isinstance(data["name"], str)

    def test_get_habit_with_offset_pagination(self, client, user, auth_headers):
        HabitFactory.create_batch(5, user=user)

        response = client.get("/habits/?limit=2&offset=4", headers=auth_headers)
        data = response.json()

        assert len(data["items"]) == 1

    def test_get_habits_without_auth(self, client):
        response = client.get("/habits/")
        assert response.status_code == 401

    def test_get_habits_invalid_token(self, client):
        response = client.get(
            "/habits/", headers={"Authorization": "Bearer wrong_token"}
        )
        assert response.status_code == 401

    def test_get_habits_blacklisted_token(self, client, user):
        response = client.post(
            "/auth/login/",
            json={
                "email": user.email,
                "password": DEFAULT_PASSWORD,
            },
        )

        token = response.json()["access_token"]

        client.post(
            "/auth/logout/",
            headers=auth(token),
        )

        response = client.get(
            "/habits/",
            headers=auth(token),
        )

        assert response.status_code == 401

    def test_user_cannot_access_other_user_habit(self, client):
        # user1
        user1 = UserFactory()
        user2 = UserFactory()

        habit = HabitFactory(user=user1)
        token2 = create_access_token({"sub": str(user2.id)})

        response = client.get(
            f"/habits/{habit.id}/", headers={"Authorization": f"Bearer {token2}"}
        )

        assert response.status_code == 404


class TestUpdateHabit:
    def test_update_habit(self, client, auth_headers, habit):
        new_name = random_habit_name()

        response = client.patch(
            f"/habits/{habit.id}/",
            json={"name": new_name, "description": "updated habit"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == habit.id
        assert data["name"] == new_name
        assert data["description"] == "updated habit"

    def test_update_only_name(self, client, auth_headers, habit):
        new_name = random_habit_name()

        response = client.patch(
            f"/habits/{habit.id}/",
            json={"name": new_name},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == new_name
        assert data["description"] == habit.description

    def test_update_habit_description(self, client, auth_headers, habit):
        response = client.patch(
            f"/habits/{habit.id}/",
            json={"description": "updated habit"},
            headers=auth_headers,
        )
        data = response.json()
        assert response.status_code == 200
        assert data["name"] == habit.name
        assert data["description"] == "updated habit"

    def test_update_habit_long_name(self, client, auth_headers, habit):
        response = client.patch(
            f"/habits/{habit.id}/", json={"name": "a" * 260}, headers=auth_headers
        )

        assert response.status_code == 422

    def test_update_habit_empty_name(self, client, auth_headers, habit):
        response = client.patch(
            f"/habits/{habit.id}/", json={"name": ""}, headers=auth_headers
        )

        assert response.status_code == 422

    def test_update_blank_name(self, client, auth_headers, habit):

        response = client.patch(
            f"/habits/{habit.id}/",
            json={
                "name": "      ",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_update_duplicate_name(self, client, auth_headers):
        h1 = create_habit(client, auth_headers)
        h2 = create_habit(client, auth_headers)

        response = client.patch(
            f"/habits/{h2['id']}/",
            json={"name": h1["name"]},
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_update_nonexistent_habit(self, client, auth_headers):
        response = client.patch(
            "/habits/999999/", json={"name": "test"}, headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_habit_invalid_token(self, client, habit):
        response = client.patch(
            f"/habits/{habit.id}/",
            json={"name": "test"},
            headers={"Authorization": "Bearer wrong_token"},
        )

        assert response.status_code == 401

    def test_update_habit_empty_json(self, client, auth_headers, habit):
        response = client.patch(f"/habits/{habit.id}/", json={}, headers=auth_headers)

        assert response.status_code == 400

    def test_user_cannot_update_other_user_habit(self, client, habit):
        other_user = register_user(client)
        token = other_user["access_token"]

        response = client.patch(
            f"/habits/{habit.id}/", json={"name": "test"}, headers=auth(token)
        )

        assert response.status_code == 404


class TestDeleteHabit:
    def test_delete_habit(self, client, auth_headers, habit):
        response = client.delete(f"/habits/{habit.id}/", headers=auth_headers)

        assert response.status_code == 204

        response = client.get(f"/habits/{habit.id}/", headers=auth_headers)

        assert response.status_code == 404

    def test_deleted_habit_is_unavailable_for_all_operations(
        self, client, auth_headers, habit
    ):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers)
        client.delete(f"/habits/{habit.id}/", headers=auth_headers)

        stats = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers)
        assert stats.status_code == 404

        patch = client.patch(
            f"/habits/{habit.id}/", json={"name": "123"}, headers=auth_headers
        )
        assert patch.status_code == 404

        deletion = client.delete(f"/habits/{habit.id}/", headers=auth_headers)
        assert deletion.status_code == 404

        mark_done = client.post(f"/habits/{habit.id}/done/", headers=auth_headers)
        assert mark_done.status_code == 404

    def test_delete_habit_wrong_id(self, client, auth_headers):
        response = client.delete("/habits/999999/", headers=auth_headers)

        assert response.status_code == 404

    def test_delete_invalid_token(self, client, habit):
        response = client.delete(
            f"/habits/{habit.id}/", headers={"Authorization": "Bearer wrong_token"}
        )

        assert response.status_code == 401

    def test_delete_no_token(self, client, habit):
        response = client.delete(f"/habits/{habit.id}/")
        assert response.status_code == 401

    def test_user_cannot_delete_other_user_habit(self, client, habit):
        other_user = register_user(client)
        token = other_user["access_token"]

        response = client.delete(f"/habits/{habit.id}/", headers=auth(token))

        assert response.status_code == 404


class TestMarkDone:
    def test_mark_done(self, client, auth_headers, habit):
        response = client.post(f"/habits/{habit.id}/done/", headers=auth_headers)
        assert response.status_code == 204

        data = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers).json()

        assert data["current_streak"] == 1
        assert data["best_streak"] == 1
        assert isinstance(data["last_7_days"], list)
        assert len(data["last_7_days"]) == 7
        assert any(day["done"] for day in data["last_7_days"])

    def test_mark_done_twice(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers)
        response = client.post(f"/habits/{habit.id}/done/", headers=auth_headers)

        assert response.status_code == 409

    def test_mark_done_other_user_habit(self, client):
        user1 = register_user(client)
        user2 = register_user(client)

        habit = client.post(
            "/habits/",
            json={"name": random_habit_name()},
            headers=auth(user1["access_token"]),
        ).json()

        response = client.post(
            f"/habits/{habit['id']}/done/",
            headers=auth(user2["access_token"]),
        )

        assert response.status_code == 404

    def test_mark_done_wrong_id(self, client, auth_headers):
        response = client.post("/habits/999999/done/", headers=auth_headers)
        assert response.status_code == 404

    def test_mark_done_wrong_token(self, client, habit):
        response = client.post(
            f"/habits/{habit.id}/done/", headers={"Authorization": "Bearer wrong_token"}
        )
        assert response.status_code == 401

    def test_mark_done_no_token(self, client, habit):
        response = client.post(f"/habits/{habit.id}/done/")

        assert response.status_code == 401


class TestUndoDone:
    def test_undo_done(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers)

        response = client.delete(f"/habits/{habit.id}/done/", headers=auth_headers)
        assert response.status_code == 204

        data = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers).json()

        assert data["current_streak"] == 0
        assert data["best_streak"] == 0

        assert isinstance(data["last_7_days"], list)
        assert all(not day["done"] for day in data["last_7_days"])

    def test_undo_recalculates_stats(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers)

        stats1 = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers).json()
        assert stats1["completion_last_7_days"] == pytest.approx(1 / 7 * 100)
        assert stats1["completion_last_30_days"] == pytest.approx(1 / 30 * 100)

        client.delete(f"/habits/{habit.id}/done/", headers=auth_headers)

        stats2 = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers).json()

        assert stats2["completion_last_7_days"] == pytest.approx(0.0)
        assert stats2["completion_last_30_days"] == pytest.approx(0.0)

    def test_double_undo(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers)
        client.delete(f"/habits/{habit.id}/done/", headers=auth_headers)

        response = client.delete(f"/habits/{habit.id}/done/", headers=auth_headers)

        assert response.status_code == 409

    def test_undo_mark_wrong(self, client, auth_headers, habit):
        response = client.delete(f"/habits/{habit.id}/done/", headers=auth_headers)
        assert response.status_code == 409

    def test_undo_wrong_id(self, client, auth_headers):
        response = client.delete("/habits/999999/done/", headers=auth_headers)

        assert response.status_code == 404

    def test_undo_mark_wrong_token(self, client, habit):
        response = client.delete(
            f"/habits/{habit.id}/done/", headers={"Authorization": "Bearer wrong_token"}
        )
        assert response.status_code == 401

    def test_undo_mark_reduces_streak(
        self, client, auth_headers, freeze_time, base_time
    ):
        email = random_email()
        with freeze_time(base_time - timedelta(days=1)):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
            response = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers)

        assert response.status_code == 200

        stats = response.json()

        assert stats["current_streak"] == 2
        assert stats["best_streak"] == 2

        with freeze_time(base_time):
            client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)
            stats = client.get(
                f"/habits/{habit_id}/stats/", headers=auth_headers
            ).json()

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 1

    def test_user_cannot_undo_other_user_habit(self, client):
        user1 = register_user(client)
        user2 = register_user(client)

        habit = client.post(
            "/habits/",
            json={"name": random_habit_name()},
            headers=auth(user1["access_token"]),
        ).json()

        client.post(
            f"/habits/{habit['id']}/done/",
            headers=auth(user1["access_token"]),
        )

        response = client.delete(
            f"/habits/{habit['id']}/done/",
            headers=auth(user2["access_token"]),
        )

        assert response.status_code == 404


class TestHabitStats:
    def test_habit_stats(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers)

        response = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["current_streak"], int)
        assert isinstance(data["best_streak"], int)
        assert isinstance(data["completion_last_7_days"], float)
        assert isinstance(data["completion_last_30_days"], float)
        assert isinstance(data["last_7_days"], list)

        assert data["current_streak"] == 1
        assert data["best_streak"] == 1
        assert len(data["last_7_days"]) == 7
        assert data["completion_last_7_days"] == pytest.approx(1 / 7 * 100)
        assert data["completion_last_30_days"] == pytest.approx(1 / 30 * 100)

    def test_streak_multiple_days(self, client, auth_headers, freeze_time, base_time):
        email = random_email()
        with freeze_time(base_time - timedelta(days=1)):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
            stats = client.get(
                f"/habits/{habit_id}/stats/", headers=auth_headers
            ).json()

        assert stats["current_streak"] == 2
        assert stats["best_streak"] == 2

    def test_user_happy_path_flow(self, client, auth_headers):
        create_response = client.post(
            "/habits/",
            json={"name": random_habit_name()},
            headers=auth_headers,
        )
        assert create_response.status_code == 201

        habit = create_response.json()

        done_response = client.post(
            f"/habits/{habit['id']}/done/", headers=auth_headers
        )
        assert done_response.status_code == 204

        stats_response = client.get(
            f"/habits/{habit['id']}/stats/", headers=auth_headers
        )
        assert stats_response.status_code == 200

        stats = stats_response.json()

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 1

    def test_stats_empty(self, client, auth_headers, habit):
        response = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["current_streak"] == 0
        assert data["best_streak"] == 0

    def test_stats_nonexistent_habit(self, client, auth_headers):
        response = client.get("/habits/999999/stats/", headers=auth_headers)

        assert response.status_code == 404

    def test_stats_no_token(self, client, habit):
        response = client.get(f"/habits/{habit.id}/stats/")

        assert response.status_code == 401

    def test_completion_percentage(self, client, auth_headers, freeze_time, base_time):
        email = random_email()
        with freeze_time(base_time):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
            stats = client.get(
                f"/habits/{habit_id}/stats/", headers=auth_headers
            ).json()

        assert stats["completion_last_7_days"] == pytest.approx(1 / 7 * 100)
        assert stats["completion_last_30_days"] == pytest.approx(1 / 30 * 100)

    def test_streak_break(self, client, auth_headers, freeze_time, base_time):
        email = random_email()
        with freeze_time(base_time - timedelta(days=2)):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
            stats = client.get(
                f"/habits/{habit_id}/stats/", headers=auth_headers
            ).json()

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 1

        assert stats["completion_last_7_days"] == pytest.approx(2 / 7 * 100)
        assert stats["completion_last_30_days"] == pytest.approx(2 / 30 * 100)

    def test_edge_last_7_days(self, client, auth_headers, freeze_time, base_time):
        email = random_email()
        with freeze_time(base_time - timedelta(days=7)):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        with freeze_time(base_time - timedelta(days=6)):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
            stats = client.get(
                f"/habits/{habit_id}/stats/", headers=auth_headers
            ).json()

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 2

        assert stats["completion_last_7_days"] == pytest.approx(2 / 7 * 100)
        assert stats["completion_last_30_days"] == pytest.approx(3 / 30 * 100)

    def test_edge_last_30_days(self, client, auth_headers, freeze_time, base_time):
        email = random_email()
        with freeze_time(base_time - timedelta(days=30)):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        with freeze_time(base_time - timedelta(days=29)):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            stats = client.get(
                f"/habits/{habit_id}/stats/", headers=auth_headers
            ).json()

        assert stats["current_streak"] == 0
        assert stats["best_streak"] == 2

        assert stats["completion_last_7_days"] == pytest.approx(0 / 7 * 100)
        assert stats["completion_last_30_days"] == pytest.approx(1 / 30 * 100)


class TestHabitHeatmap:
    def test_habit_heatmap(self, client, auth_headers, habit):
        response = client.get(
            f"/habits/{habit.id}/heatmap/",
            headers=auth_headers,
        )

        assert response.status_code == 200

        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 30

        item = data[0]

        assert "date" in item
        assert "done" in item

        assert isinstance(item["date"], str)
        assert isinstance(item["done"], bool)

    def test_heatmap_reflects_done(self, client, auth_headers, habit):
        client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
        )

        data = client.get(
            f"/habits/{habit.id}/heatmap/",
            headers=auth_headers,
        ).json()

        today = date.today().isoformat()

        today_entry = next(day for day in data if day["date"] == today)

        assert today_entry["done"] is True


# Helper


def get_habit_id(client, auth_headers):
    habit = create_habit(client, auth_headers)
    return habit["id"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}
