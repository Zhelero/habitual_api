import uuid

import pytest


# Positive cases

def test_create_habit(client, auth_headers):
    response = client.post("/habits/", json={
        "name": random_habit_name(),
        "description": "Test habit"
    }, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    assert isinstance(data["id"], int)
    assert isinstance(data["name"], str)
    assert isinstance(data["description"], str)

def test_get_habits(client, auth_headers):
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

def test_get_habit_by_id(client, auth_headers):
    res = create_habit(client, auth_headers)

    habit_id = res["id"]
    response = client.get(f"/habits/{habit_id}/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == habit_id
    assert isinstance(data["name"], str)

def test_update_habit(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]
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

def test_delete_habit(client, auth_headers):
    res = create_habit(client, auth_headers)

    habit_id = res["id"]

    response = client.delete(f"/habits/{habit_id}/", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/habits/{habit_id}/", headers=auth_headers)
    assert response.status_code == 404

def test_mark_done(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]

    response = client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
    assert response.status_code == 204

    stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers)

    data = stats.json()
    assert data["current_streak"] == 1
    assert data["best_streak"] == 1
    assert isinstance(data["last_7_days"], list)
    assert len(data["last_7_days"]) == 7

def test_undo_done(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]

    client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

    response = client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)
    assert response.status_code == 204

    stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers)
    data = stats.json()

    assert data["current_streak"] == 0
    assert data["best_streak"] == 0
    assert data["completion_last_7_days"] == pytest.approx(0.0)
    assert data["completion_last_30_days"] == pytest.approx(0.0)
    assert isinstance(data["last_7_days"], list)
    assert all(not day["done"] for day in data["last_7_days"])

def test_undo_affects_stats(client, auth_headers):
    res = create_habit(client, auth_headers)

    habit_id = res["id"]

    client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
    client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)

    stats = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers).json()

    assert stats["current_streak"] == 0
    assert stats["best_streak"] == 0
    assert stats["completion_last_7_days"] == pytest.approx(0.0)
    assert stats["completion_last_30_days"] == pytest.approx(0.0)
    assert all(not day["done"] for day in stats["last_7_days"])


def test_habit_stats(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]

    client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

    response = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["current_streak"], int)
    assert isinstance(data["best_streak"], int)
    assert isinstance(data["completion_last_7_days"], float)
    assert isinstance(data["completion_last_30_days"], float)
    assert isinstance(data["last_7_days"], list)

def test_habit_heatmap(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]

    response = client.get(f"/habits/{habit_id}/heatmap/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)

    if len(data) > 0:
        item = data[0]
        assert "date" in item
        assert "done" in item
        assert isinstance(item["done"], bool)

def test_dashboard_stats(client, auth_headers):
    response = client.get("/dashboard/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["total_habits"], int)
    assert isinstance(data["completed_today"], int)
    assert isinstance(data["best_streak"], int)

def test_dashboard_with_data(client, auth_headers):
    for _ in range(3):
        create_habit(client, auth_headers)

    habits = client.get("/habits/", headers=auth_headers).json()["items"]
    habit_id = habits[0]["id"]

    client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

    response = client.get("/dashboard/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_habits"] == 3
    assert data["completed_today"] == 1

def test_user_cannot_access_other_user_habit(client):
    #user1
    res1 = client.post("/auth/register", json={
        "email": random_email(),
        "password": "123456",
    })

    token1 = res1.json()["access_token"]

    #user1 creates habit
    res = client.post("/habits/", json={
        "name": random_habit_name(),
    }, headers={"Authorization": f"Bearer {token1}"})

    habit_id = res.json()["id"]

    #user2
    res2 = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456",
    })
    token2 = res2.json()["access_token"]

    #user2 tries to get habit

    response = client.get(f"/habits/{habit_id}/", headers={
        "Authorization": f"Bearer {token2}"})

    assert response.status_code == 404

def test_mark_done_other_user_habit(client):
    res1 = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456",
    })
    token1 = res1.json()["access_token"]
    habit = client.post("/habits/", json={
        "name": random_habit_name(),
    }, headers={"Authorization": f"Bearer {token1}"}).json()

    res2 = client.post("/auth/register/", json={
        "email": random_email(),
        "password": "123456",
    })
    token2 = res2.json()["access_token"]
    habit_id = habit["id"]
    response = client.post(f"/habits/{habit_id}/done/", headers={
        "Authorization": f"Bearer {token2}"
    })

    assert response.status_code == 404

# Negative

def test_habits_without_auth(client):
    res = client.get("/habits/")
    assert res.status_code == 401

def test_create_habit_empty_name(client, auth_headers):
    response = client.post("/habits/", json={
        "name": ""
    },headers=auth_headers)

    assert response.status_code in (400, 422)

def test_update_habit_empty_name(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]

    response = client.patch(f"/habits/{habit_id}/", json={
        "name": ""
    }, headers=auth_headers)

    assert response.status_code == 422

def test_update_nonexistent_habit(client, auth_headers):
    response = client.patch("/habits/123/", json={
        "name": "test"
    }, headers=auth_headers)

    assert response.status_code == 404

def test_delete_habit_wrong_id(client, auth_headers):
    response = client.delete("/habits/123/", headers=auth_headers)

    assert response.status_code == 404

def test_mark_done_twice(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]

    client.post(f"/habits/{habit_id}/done/", headers=auth_headers)
    response = client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

    assert response.status_code == 409

def test_undo_mark_wrong(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]

    response = client.delete(f"/habits/{habit_id}/done/", headers=auth_headers)
    assert response.status_code == 409

def test_stats_empty(client, auth_headers):
    response = create_habit(client, auth_headers)

    habit_id = response["id"]

    response = client.get(f"/habits/{habit_id}/stats/", headers=auth_headers)
    data = response.json()

    assert data["current_streak"] == 0
    assert data["best_streak"] == 0


# HELPERS

def random_habit_name():
    return f"habit {uuid.uuid4()}"

def random_email():
    return f"{uuid.uuid4()}@test.com"

def create_habit(client, headers, name=None):
    res = client.post("/habits/", json={
        "name": name or random_habit_name(),
    }, headers=headers)

    assert res.status_code == 201
    return res.json()
