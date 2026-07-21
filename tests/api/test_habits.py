import pytest

from app.core.jwt import create_access_token
from app.db.models import HabitLog
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
from datetime import timedelta, datetime, timezone


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

    def test_create_habit_with_color(self, client, auth_headers):
        response = client.post(
            "/habits/",
            json={"name": random_habit_name(), "color": "blue"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["color"] == "blue"

    def test_create_habit_without_color_defaults_to_null(self, client, auth_headers):
        response = client.post(
            "/habits/", json={"name": random_habit_name()}, headers=auth_headers
        )

        assert response.status_code == 201
        assert response.json()["color"] is None

    def test_create_habit_invalid_color(self, client, auth_headers):
        response = client.post(
            "/habits/",
            json={"name": random_habit_name(), "color": "neon"},
            headers=auth_headers,
        )

        assert response.status_code == 422

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

    def test_update_habit_color(self, client, auth_headers, habit):
        response = client.patch(
            f"/habits/{habit.id}/",
            json={"color": "emerald"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == habit.name
        assert data["color"] == "emerald"

    def test_update_habit_invalid_color(self, client, auth_headers, habit):
        response = client.patch(
            f"/habits/{habit.id}/",
            json={"color": "neon"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_clear_habit_color(self, client, auth_headers, habit):
        client.patch(
            f"/habits/{habit.id}/", json={"color": "rose"}, headers=auth_headers
        )

        response = client.patch(
            f"/habits/{habit.id}/", json={"color": None}, headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["color"] is None

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


class TestArchiveHabit:
    def test_archive_habit(self, client, auth_headers, habit):
        response = client.patch(
            f"/habits/{habit.id}/archive/",
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_archived_habit_excluded_from_list(self, client, auth_headers, habit):
        client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)

        response = client.get("/habits/", headers=auth_headers)
        data = response.json()

        ids = [h["id"] for h in data["items"]]
        assert habit.id not in ids

    def test_archived_habit_included_when_requested(self, client, auth_headers, habit):
        client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)

        response = client.get("/habits/?filter=all", headers=auth_headers)
        data = response.json()

        ids = [h["id"] for h in data["items"]]
        assert habit.id in ids

    def test_archived_habit_still_accessible_by_id(self, client, auth_headers, habit):
        client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)

        response = client.get(f"/habits/{habit.id}/", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["is_archived"] is True

    def test_archive_nonexistent_habit(self, client, auth_headers):
        response = client.patch("/habits/999999/archive/", headers=auth_headers)

        assert response.status_code == 404

    def test_archive_habit_invalid_token(self, client, habit):
        response = client.patch(
            f"/habits/{habit.id}/archive/",
            headers={"Authorization": "Bearer wrong_token"},
        )

        assert response.status_code == 401

    def test_user_cannot_archive_other_user_habit(self, client, habit):
        other_user = register_user(client)
        token = other_user["access_token"]

        response = client.patch(f"/habits/{habit.id}/archive/", headers=auth(token))

        assert response.status_code == 404

    def test_archive_already_archived_habit(self, client, auth_headers, habit):
        client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)

        response = client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)

        assert response.status_code == 204


class TestRestoreHabit:
    def test_restore_habit(self, client, auth_headers, habit):
        client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)

        response = client.patch(f"/habits/{habit.id}/restore/", headers=auth_headers)

        assert response.status_code == 204

        response = client.get(
            f"/habits/{habit.id}/",
            headers=auth_headers,
        )

        assert response.json()["is_archived"] is False

    def test_restored_habit_appears_in_list(self, client, auth_headers, habit):
        client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)
        client.patch(f"/habits/{habit.id}/restore/", headers=auth_headers)

        response = client.get("/habits/", headers=auth_headers)
        data = response.json()

        ids = [h["id"] for h in data["items"]]
        assert habit.id in ids

    def test_restore_active_habit(self, client, auth_headers, habit):
        response = client.patch(f"/habits/{habit.id}/restore/", headers=auth_headers)

        assert response.status_code == 204

    def test_restore_nonexistent_habit(self, client, auth_headers):
        response = client.patch("/habits/999999/restore/", headers=auth_headers)

        assert response.status_code == 404

    def test_restore_habit_invalid_token(self, client, habit):
        response = client.patch(
            f"/habits/{habit.id}/restore/",
            headers={"Authorization": "Bearer wrong_token"},
        )

        assert response.status_code == 401

    def test_user_cannot_restore_other_user_habit(self, client, habit):
        other_user = register_user(client)
        token = other_user["access_token"]

        response = client.patch(f"/habits/{habit.id}/restore/", headers=auth(token))

        assert response.status_code == 404

    def test_restore_returns_habit_to_total(self, client, auth_headers):
        h1 = create_habit(client, auth_headers)

        client.patch(
            f"/habits/{h1['id']}/archive/",
            headers=auth_headers,
        )

        client.patch(
            f"/habits/{h1['id']}/restore/",
            headers=auth_headers,
        )

        response = client.get("/habits/", headers=auth_headers)

        assert response.json()["total"] == 1


class TestListHabitsArchiveFilter:
    def test_total_excludes_archived_by_default(self, client, auth_headers):
        create_habit(client, auth_headers)
        h2 = create_habit(client, auth_headers)

        client.patch(f"/habits/{h2['id']}/archive/", headers=auth_headers)

        response = client.get("/habits/", headers=auth_headers)
        assert response.json()["total"] == 1

    def test_total_includes_archived_when_requested(self, client, auth_headers):
        create_habit(client, auth_headers)
        h2 = create_habit(client, auth_headers)

        client.patch(f"/habits/{h2['id']}/archive/", headers=auth_headers)

        response = client.get("/habits/?filter=all", headers=auth_headers)
        assert response.json()["total"] == 2


class TestMarkDone:
    def test_mark_done(self, client, auth_headers, habit):
        response = client.post(
            f"/habits/{habit.id}/done/", headers=auth_headers, json={}
        )
        assert response.status_code == 204

        data = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers).json()

        assert data["current_streak"] == 1
        assert data["best_streak"] == 1
        assert isinstance(data["last_7_days"], list)
        assert len(data["last_7_days"]) == 7
        assert any(day["done"] for day in data["last_7_days"])

    def test_mark_done_with_note(self, client, auth_headers, habit, db):
        response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Morning run  "},
        )

        assert response.status_code == 204

        log = db.query(HabitLog).filter(HabitLog.habit_id == habit.id).one()

        assert log.note == "Morning run"

    def test_mark_done_blank_note_becomes_none(self, client, auth_headers, habit, db):
        response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "  "},
        )

        assert response.status_code == 204

        log = db.query(HabitLog).filter(HabitLog.habit_id == habit.id).one()

        assert log.note is None

    def test_mark_done_twice(self, client, auth_headers, habit):
        response = client.post(
            f"/habits/{habit.id}/done/", headers=auth_headers, json={}
        )

        assert response.status_code == 204

        response = client.post(
            f"/habits/{habit.id}/done/", headers=auth_headers, json={}
        )

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
            json={},
        )

        assert response.status_code == 404

    def test_mark_done_wrong_id(self, client, auth_headers):
        response = client.post("/habits/999999/done/", headers=auth_headers, json={})
        assert response.status_code == 404

    def test_mark_done_requires_body(self, client, habit, auth_headers):
        response = client.post(f"/habits/{habit.id}/done/", headers=auth_headers)

        assert response.status_code == 422

    def test_mark_done_wrong_token(self, client, habit):
        response = client.post(
            f"/habits/{habit.id}/done/",
            headers={"Authorization": "Bearer wrong_token"},
            json={},
        )
        assert response.status_code == 401

    def test_mark_done_no_token(self, client, habit):
        response = client.post(f"/habits/{habit.id}/done/", json={})

        assert response.status_code == 401


class TestUpdateHabitLogNote:
    def test_update_habit_log_note(self, client, auth_headers, habit):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Morning run"},
        )

        assert create_response.status_code == 204

        response = client.patch(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Midnight sleep   "},
        )

        assert response.status_code == 204

        data = client.get(
            f"/habits/{habit.id}/heatmap/",
            headers=auth_headers,
        ).json()

        today_log = next(
            item
            for item in data
            if item["date"] == datetime.now(timezone.utc).date().isoformat()
        )
        assert today_log["note"] == "Midnight sleep"

    def test_update_habit_log_note_from_text_to_none(self, client, auth_headers, habit):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Morning run"},
        )

        assert create_response.status_code == 204

        response = client.patch(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "   "},
        )

        assert response.status_code == 204

        data = client.get(
            f"/habits/{habit.id}/heatmap/",
            headers=auth_headers,
        ).json()

        today_log = next(
            item
            for item in data
            if item["date"] == datetime.now(timezone.utc).date().isoformat()
        )
        assert today_log["note"] is None

    def test_update_habit_log_without_note(self, client, auth_headers, habit):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Morning run"},
        )

        assert create_response.status_code == 204

        response = client.patch(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 204

        data = client.get(
            f"/habits/{habit.id}/heatmap/",
            headers=auth_headers,
        ).json()

        today_log = next(
            item
            for item in data
            if item["date"] == datetime.now(timezone.utc).date().isoformat()
        )
        assert today_log["note"] is None

    def test_update_habit_log_note_from_none_to_text(self, client, auth_headers, habit):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={},
        )

        assert create_response.status_code == 204

        response = client.patch(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Something is happening"},
        )

        assert response.status_code == 204

        data = client.get(
            f"/habits/{habit.id}/heatmap/",
            headers=auth_headers,
        ).json()

        today_log = next(
            item
            for item in data
            if item["date"] == datetime.now(timezone.utc).date().isoformat()
        )
        assert today_log["note"] == "Something is happening"

    def test_update_archived_habit_log_note(self, client, auth_headers, habit):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Good morning"},
        )

        assert create_response.status_code == 204

        archive_response = client.patch(
            f"/habits/{habit.id}/archive/",
            headers=auth_headers,
        )

        assert archive_response.status_code == 204

        response = client.patch(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Well done"},
        )

        assert response.status_code == 204

        data = client.get(
            f"/habits/{habit.id}/heatmap/",
            headers=auth_headers,
        ).json()

        today_log = next(
            item
            for item in data
            if item["date"] == datetime.now(timezone.utc).date().isoformat()
        )
        assert today_log["note"] == "Well done"

    def test_update_habit_log_note_accepts_500_chars(self, client, auth_headers, habit):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Morning run"},
        )

        assert create_response.status_code == 204

        response = client.patch(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "a" * 500},
        )

        assert response.status_code == 204

        data = client.get(
            f"/habits/{habit.id}/heatmap/",
            headers=auth_headers,
        ).json()

        today_log = next(
            item
            for item in data
            if item["date"] == datetime.now(timezone.utc).date().isoformat()
        )
        assert today_log["note"] == "a" * 500

    def test_update_habit_log_note_rejects_too_long_note(
        self, client, auth_headers, habit
    ):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={},
        )

        assert create_response.status_code == 204

        response = client.patch(
            f"/habits/{habit.id}/done/", json={"note": "a" * 501}, headers=auth_headers
        )

        assert response.status_code == 422

    def test_update_unmarked_habit_log_note(self, client, auth_headers, habit):
        response = client.patch(
            f"/habits/{habit.id}/done/",
            json={"note": "It's done"},
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_update_another_habit_log_note(self, client, auth_headers, habit):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={},
        )

        assert create_response.status_code == 204

        new_habit = client.post(
            "/habits/",
            json={"name": "Hello"},
            headers=auth_headers,
        ).json()

        response = client.patch(
            f"/habits/{new_habit['id']}/done/",
            json={"note": "It's done"},
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_update_nonexistent_habit_log_note(self, client, auth_headers, habit):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={},
        )

        assert create_response.status_code == 204

        response = client.patch(
            "/habits/999999/done/", json={"note": "It's done"}, headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_other_user_habit_log_note(self, client):
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
            json={},
        )

        response = client.patch(
            f"/habits/{habit['id']}/done/",
            headers=auth(user2["access_token"]),
            json={"note": "It's done"},
        )

        assert response.status_code == 404

    def test_update_habit_log_note_requires_body(self, client, habit, auth_headers):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={},
        )

        assert create_response.status_code == 204

        response = client.patch(f"/habits/{habit.id}/done/", headers=auth_headers)

        assert response.status_code == 422

    def test_update_habit_log_note_wrong_token(self, client, habit, auth_headers):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={},
        )

        assert create_response.status_code == 204

        response = client.patch(
            f"/habits/{habit.id}/done/",
            headers={"Authorization": "Bearer wrong_token"},
            json={},
        )
        assert response.status_code == 401

    def test_update_habit_log_note_no_token(self, client, habit, auth_headers):
        create_response = client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={},
        )

        assert create_response.status_code == 204

        response = client.patch(f"/habits/{habit.id}/done/", json={})

        assert response.status_code == 401


class TestUndoDone:
    def test_undo_done(self, client, auth_headers, habit):
        client.post(
            f"/habits/{habit.id}/done/",
            headers=auth_headers,
            json={"note": "Did something"},
        )

        response = client.delete(f"/habits/{habit.id}/done/", headers=auth_headers)
        assert response.status_code == 204

        data = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers).json()

        assert data["current_streak"] == 0
        assert data["best_streak"] == 0

        assert isinstance(data["last_7_days"], list)
        assert all(not day["done"] for day in data["last_7_days"])

    def test_undo_recalculates_stats(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers, json={})

        stats1 = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers).json()
        assert stats1["completion_last_7_days"] == pytest.approx(1 / 7 * 100)
        assert stats1["completion_last_30_days"] == pytest.approx(1 / 30 * 100)

        client.delete(f"/habits/{habit.id}/done/", headers=auth_headers)

        stats2 = client.get(f"/habits/{habit.id}/stats/", headers=auth_headers).json()

        assert stats2["completion_last_7_days"] == pytest.approx(0.0)
        assert stats2["completion_last_30_days"] == pytest.approx(0.0)

    def test_double_undo(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers, json={})
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
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})
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


class TestMarkDoneArchivedHabit:
    def test_mark_done_archived_habit_returns_409(self, client, auth_headers, habit):
        client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)

        response = client.post(
            f"/habits/{habit.id}/done/", headers=auth_headers, json={}
        )

        assert response.status_code == 409

    def test_undo_done_archived_habit_returns_409(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers)
        client.patch(f"/habits/{habit.id}/archive/", headers=auth_headers)

        response = client.delete(f"/habits/{habit.id}/done/", headers=auth_headers)

        assert response.status_code == 409


class TestHabitStats:
    def test_habit_stats(self, client, auth_headers, habit):
        client.post(f"/habits/{habit.id}/done/", headers=auth_headers, json={})

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
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})
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
            f"/habits/{habit['id']}/done/",
            headers=auth_headers,
            json={},
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
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})
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
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})
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
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})

        with freeze_time(base_time - timedelta(days=6)):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})

        with freeze_time(base_time):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})
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
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})

        with freeze_time(base_time - timedelta(days=29)):
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers, json={})

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

        assert all("date" in item for item in data)
        assert all("done" in item for item in data)
        assert all("note" in item for item in data)

        assert all(isinstance(item["date"], str) for item in data)
        assert all(isinstance(item["done"], bool) for item in data)
        assert all(
            isinstance(item["note"], str) or item["note"] is None for item in data
        )

    def test_heatmap_reflects_done_without_note(
        self, client, auth_headers, freeze_time, base_time
    ):
        email = random_email()
        with freeze_time(base_time):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            response = client.post(
                f"/habits/{habit_id}/done/",
                headers=auth_headers,
                json={"note": None},
            )
            assert response.status_code == 204

            data = client.get(
                f"/habits/{habit_id}/heatmap/",
                headers=auth_headers,
            ).json()

            today = base_time.date().isoformat()

            today_entry = next(day for day in data if day["date"] == today)

            assert today_entry["done"] is True
            assert today_entry["note"] is None

    def test_heatmap_reflects_done_with_note(
        self, client, auth_headers, freeze_time, base_time
    ):
        email = random_email()
        note = "Something new"
        with freeze_time(base_time):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            response = client.post(
                f"/habits/{habit_id}/done/",
                headers=auth_headers,
                json={"note": note},
            )
            assert response.status_code == 204

            data = client.get(
                f"/habits/{habit_id}/heatmap/",
                headers=auth_headers,
            ).json()

            today = base_time.date().isoformat()

            today_entry = next(day for day in data if day["date"] == today)

            assert today_entry["done"] is True
            assert today_entry["note"] == note


# Helper


def get_habit_id(client, auth_headers):
    habit = create_habit(client, auth_headers)
    return habit["id"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}
