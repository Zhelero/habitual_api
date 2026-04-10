import pytest

from tests.services.test_auth_service import DEFAULT_PASSWORD
from tests.utils.helpers import create_habit, random_habit_name, register_user, get_auth_headers, random_email
from datetime import timedelta


class TestCreateHabit:
    def test_create_habit(self, client, auth_headers):
        response = client.post("/habits/", json={
            "name": random_habit_name(),
            "description": "Test habit"
        }, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()

        assert isinstance(data["id"], int)
        assert isinstance(data["name"], str)
        assert isinstance(data["description"], str)

    def test_create_habit_empty_name(self, client, auth_headers):
        response = client.post("/habits/", json={
            "name": ""
        }, headers=auth_headers)

        assert response.status_code in (400, 422)

    def test_create_habit_long_name(self, client, auth_headers):
        response = client.post("/habits/", json={
            "name": "a" * 260
        }, headers=auth_headers)

        assert response.status_code == 422

    def test_create_habit_duplicate_name(self, client, auth_headers):
        name = random_habit_name()
        client.post("/habits/", json={
            "name": name
        }, headers=auth_headers)

        response = client.post("/habits/", json={
            "name": name
        }, headers=auth_headers)

        assert response.status_code == 409

    def test_create_habit_invalid_token(self, client, auth_headers):
        response = client.post("/habits/", json={
            "name": random_habit_name(),
        }, headers={
            "Authorization": "wrong_token"
        })

        assert response.status_code == 401


class TestGetHabits:
    def test_get_habits(self, client, auth_headers):
        for _ in range(5):
            create_habit(client, auth_headers)

        response = client.get("/habits/?limit=2&offset=0", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["items"], list)
        assert len(data["items"]) == 2
        assert data["total"] >= 5

        item = data["items"][0]
        assert "id" in item
        assert "name" in item

    def test_get_habit_by_id(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)
        response = client.get(f"/habits/{habit_id}/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == habit_id
        assert isinstance(data["name"], str)

    def test_pagination_offset(self, client, auth_headers):
        for _ in range(5):
            create_habit(client, auth_headers)

        response = client.get("/habits/?limit=2&offset=4", headers=auth_headers).json()
        data = response

        assert len(data["items"]) <= 2

    def test_get_habits_without_auth(self, client):
        response = client.get("/habits/")
        assert response.status_code == 401

    def test_get_habits_invalid_token(self, client):
        response = client.get("/habits/", headers={
            "Authorization": "wrong_token"
        })
        assert response.status_code == 401

    def test_get_habits_blacklisted_token(self, client):
        user = register_user(client)
        token = user["access_token"]

        client.post("/auth/logout/", headers=auth(token))
        response = client.get("/habits/", headers=auth(token))

        assert response.status_code == 401

    def test_user_cannot_access_other_user_habit(self, client):
        #user1
        user1 = register_user(client)

        token1 = user1["access_token"]

        #user1 creates habit
        response = client.post("/habits/", json={
            "name": random_habit_name(),
        }, headers=auth(token1))

        habit_id = response.json()["id"]

        #user2
        user2 = register_user(client)
        token2 = user2["access_token"]

        #user2 tries to get habit

        response = client.get(f"/habits/{habit_id}/", headers=auth(token2))

        assert response.status_code == 404


class TestUpdateHabit:
    def test_update_habit(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)
        new_name = random_habit_name()

        response = client.patch(f"/habits/{habit_id}/", json={
            "name": new_name,
            "description": "updated habit"
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == habit_id
        assert data["name"] == new_name
        assert data["description"] == "updated habit"

    def test_update_habit_description(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)
        response = client.patch(f"/habits/{habit_id}/", json={
            "description": "updated habit"
        }, headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["description"] == "updated habit"

    def test_update_habit_empty_name(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.patch(f"/habits/{habit_id}/", json={
            "name": ""
        }, headers=auth_headers)

        assert response.status_code == 422

    def test_update_nonexistent_habit(self, client, auth_headers):
        response = client.patch("/habits/123/", json={
            "name": "test"
        }, headers=auth_headers)

        assert response.status_code == 404

    def test_update_habit_invalid_token(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)
        response = client.patch(f"/habits/{habit_id}/", json={
            "name": "test"
        }, headers={
            "Authorization": "wrong_token"
        })

        assert response.status_code == 401


class TestDeleteHabit:
    def test_delete_habit(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.delete(f"/habits/{habit_id}/", headers=auth_headers)
        assert response.status_code == 204

        response = client.get(f"/habits/{habit_id}/", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_habit_remove_stats(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
        client.delete(f"/habits/{habit_id}/", headers=auth_headers)

        response = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_habit_wrong_id(self, client, auth_headers):
        response = client.delete("/habits/123/", headers=auth_headers)

        assert response.status_code == 404

    def test_delete_invalid_token(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.delete(f"/habits/{habit_id}/", headers={
            "Authorization": "wrong_token"
        })

        assert response.status_code == 401

    def test_delete_no_token(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.delete(f"/habits/{habit_id}/", headers={})
        assert response.status_code == 401


class TestMarkDone:
    def test_mark_done(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
        assert response.status_code == 204

        stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()
        data = stats

        assert data["current_streak"] == 1
        assert data["best_streak"] == 1
        assert isinstance(data["last_7_days"], list)
        assert len(data["last_7_days"]) == 7

    def test_mark_done_twice(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
        response = client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        assert response.status_code == 409

    def test_mark_done_race_condition(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        responses = [
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers),
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers),
        ]
        statuses = [r.status_code for r in responses]

        assert 204 in statuses
        assert 409 in statuses

    def test_mark_done_other_user_habit(self, client):
        user1 = register_user(client)
        token1 = user1["access_token"]
        habit = client.post("/habits/", json={
            "name": random_habit_name(),
        }, headers=auth(token1)).json()

        user2 = register_user(client)
        token2 = user2["access_token"]
        habit_id = habit["id"]
        response = client.post(f"/habits/{habit_id}/done/", headers=auth(token2))

        assert response.status_code == 404

    def test_mark_done_wrong_id(self, client, auth_headers):
        response = client.post("/habits/123/done", headers=auth_headers)
        assert response.status_code == 404

    def test_mark_done_wrong_token(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)
        response = client.post(f"/habits/{habit_id}/done/", headers={
            "Authorization": "wrong_token"
        })
        assert response.status_code == 401


class TestUndoDone:
    def test_undo_done(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        response = client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)
        assert response.status_code == 204

        stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()
        data = stats

        assert data["current_streak"] == 0
        assert data["best_streak"] == 0
        assert data["completion_last_7_days"] == pytest.approx(0.0)
        assert data["completion_last_30_days"] == pytest.approx(0.0)
        assert isinstance(data["last_7_days"], list)
        assert all(not day["done"] for day in data["last_7_days"])

    def test_undo_affects_stats(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
        client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)

        stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()

        assert stats["current_streak"] == 0
        assert stats["best_streak"] == 0
        assert stats["completion_last_7_days"] == pytest.approx(0.0)
        assert stats["completion_last_30_days"] == pytest.approx(0.0)
        assert all(not day["done"] for day in stats["last_7_days"])

    def test_double_undo(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
        client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)

        response = client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)

        assert response.status_code == 409

    def test_undo_mark_wrong(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)
        assert response.status_code == 409

    def test_undo_mark_wrong_token(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.delete(f"/habits/{habit_id}/done/", headers={
            "Authorization": "wrong_token"
        })
        assert response.status_code == 401

    def test_undo_mark_reduces_streak(self, client, auth_headers, freeze_time, base_time):
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
        print(stats)
        assert stats["current_streak"] == 2
        assert stats["best_streak"] == 2

        with freeze_time(base_time):
            client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)
            stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()


        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 1


class TestHabitStats:
    def test_habit_stats(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        response = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["current_streak"], int)
        assert isinstance(data["best_streak"], int)
        assert isinstance(data["completion_last_7_days"], float)
        assert isinstance(data["completion_last_30_days"], float)
        assert isinstance(data["last_7_days"], list)

        assert data["current_streak"] == 1
        assert data["best_streak"] == 1
        assert data["completion_last_7_days"] == pytest.approx(1/7 * 100)
        assert data["completion_last_30_days"] == pytest.approx(1/30 * 100)


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
            stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()

        assert stats["current_streak"] == 2
        assert stats["best_streak"] == 2

    def test_user_flow(self, client):
        user = register_user(client)
        token = user["access_token"]

        habit = client.post("/habits/", json={
            "name": random_habit_name(),
        }, headers=auth(token)).json()
        habit_id = habit["id"]

        client.post(f"/habits/{habit_id}/done/", headers=auth(token))

        stats = client.get(f"/habits/{habit_id}/stats/", headers=auth(token)).json()

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 1

    def test_stats_empty(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()
        data = response

        assert data["current_streak"] == 0
        assert data["best_streak"] == 0

    def test_completion_percentage(self, client, auth_headers, freeze_time, base_time):
        email = random_email()
        with freeze_time(base_time):
            register_user(client, email, DEFAULT_PASSWORD)
            auth_headers = get_auth_headers(client, email, DEFAULT_PASSWORD)
            habit_id = get_habit_id(client, auth_headers)
            client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
            stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()

        assert stats["completion_last_7_days"] == pytest.approx(1/7 * 100)
        assert stats["completion_last_30_days"] == pytest.approx(1/30 * 100)

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
            stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 1

        assert stats["completion_last_7_days"] == pytest.approx(2/7 * 100)
        assert stats["completion_last_30_days"] == pytest.approx(2/30 * 100)

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
            stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()

        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 2

        assert stats["completion_last_7_days"] == pytest.approx(2/7 * 100)
        assert stats["completion_last_30_days"] == pytest.approx(3/30 * 100)

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
            stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()

        assert stats["current_streak"] == 0
        assert stats["best_streak"] == 2

        assert stats["completion_last_7_days"] == pytest.approx(0/7 * 100)
        assert stats["completion_last_30_days"] == pytest.approx(1/30 * 100)

class TestHabitHeatmap:
    def test_habit_heatmap(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        response = client.get(f"/habits/{habit_id}/heatmap/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

        if len(data) > 0:
            item = data[0]
            assert "date" in item
            assert "done" in item
            assert isinstance(item["done"], bool)

    def test_heatmap_reflects_done(self, client, auth_headers):
        habit_id = get_habit_id(client, auth_headers)

        client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

        data = client.get(f"/habits/{habit_id}/heatmap/", headers=auth_headers).json()

        assert any(day["done"] for day in data)


# Helper

def get_habit_id(client, auth_headers):
    habit = create_habit(client, auth_headers)
    return habit["id"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}