from datetime import timedelta

from tests.utils.helpers import create_habit, register_user, get_auth_headers, random_email

def test_dashboard_stats(client, auth_headers):
    response = client.get("/dashboard/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == {
        "total_habits",
        "completed_today",
        "best_streak"
    }

    assert isinstance(data["total_habits"], int)
    assert isinstance(data["completed_today"], int)
    assert isinstance(data["best_streak"], int)

def test_dashboard_with_data(client, auth_headers):
    habits = [create_habit(client, auth_headers) for _ in range(3)]

    habit_id = habits[0]["id"]

    client.post(f"/habits/{habit_id}/done/", headers=auth_headers)

    response = client.get("/dashboard/", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()

    assert data["total_habits"] == 3
    assert data["completed_today"] == 1
    assert data["best_streak"] == 1

def test_dashboard_empty(client, auth_headers):
    response = client.get("/dashboard/", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()
    assert data["total_habits"] == 0
    assert data["completed_today"] == 0
    assert data["best_streak"] == 0

def test_dashboard_no_token(client):
    response = client.get("/dashboard/")

    assert response.status_code == 401

class TestAuth:
    def test_invalid_token(self, client):
        response = client.get("/dashboard/", headers={
            "Authorization": "Bearer invalid token"
        })
        assert response.status_code == 401

    def test_blacklisted_token(self, client):
        user = register_user(client)
        token = user["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/auth/logout/", headers=headers)
        response = client.get("/dashboard/", headers=headers)

        assert response.status_code == 401

class TestIsolation:
    def test_users_see_only_own_habits(self, client):
        user1 = register_user(client)
        user2 = register_user(client)
        h1 = {"Authorization": f"Bearer {user1['access_token']}"}
        h2 = {"Authorization": f"Bearer {user2['access_token']}"}

        for _ in range(3):
            create_habit(client, h1)
        create_habit(client, h2)

        data1 = client.get("/dashboard/", headers=h1).json()
        data2 = client.get("/dashboard/", headers=h2).json()

        assert data1["total_habits"] == 3
        assert data2["total_habits"] == 1

    def test_completed_today_isolated(self, client):
        user1 = register_user(client)
        user2 = register_user(client)
        h1 = {"Authorization": f"Bearer {user1['access_token']}"}
        h2 = {"Authorization": f"Bearer {user2['access_token']}"}

        habit = create_habit(client, h1)
        client.post(f"/habits/{habit['id']}/done/", headers=h1)

        data1 = client.get("/dashboard/", headers=h1).json()
        data2 = client.get("/dashboard/", headers=h2).json()

        assert data1["total_habits"] == 1
        assert data1["completed_today"] == 1

        assert data2["total_habits"] == 0
        assert data2["completed_today"] == 0


class TestCompletedToday:
    def test_undo_decrements_completed_today(self, client, auth_headers):
        habit = create_habit(client, auth_headers)
        client.post(f"/habits/{habit['id']}/done/", headers=auth_headers)

        data_before = client.get("/dashboard/", headers=auth_headers).json()
        assert data_before["total_habits"] == 1
        assert data_before["completed_today"] == 1

        client.delete(f"/habits/{habit['id']}/done/", headers=auth_headers)

        data_after =client.get("/dashboard/", headers=auth_headers).json()
        assert data_after["total_habits"] == 1
        assert data_after["completed_today"] == 0

    def test_multiple_habits_completed_today(self, client, auth_headers):
        habits = [create_habit(client, auth_headers) for _ in range(4)]

        for h in habits[:3]:
            client.post(f"/habits/{h['id']}/done/", headers=auth_headers)

        data = client.get("/dashboard/", headers=auth_headers).json()

        assert data["total_habits"] == 4
        assert data["completed_today"] == 3
        assert data["best_streak"] == 1

    def test_completed_today_boundary(self, client, freeze_time, base_time):
        email = random_email()
        password = "123456"
        midnight = base_time.replace(hour=23, minute=59)

        register_user(client, email, password)
        headers = get_auth_headers(client, email, password)
        habit = create_habit(client, headers)

        with freeze_time(midnight):
            headers = get_auth_headers(client, email, password)
            client.post(f"/habits/{habit['id']}/done/", headers=headers)

        with freeze_time(midnight + timedelta(minutes=3)):
            data = client.get("/dashboard/", headers=headers).json()

        assert data["total_habits"] == 1
        assert data["completed_today"] == 0
        assert data["best_streak"] == 1

    def test_dashboard_after_duplicate_mark(self, client, auth_headers):
        habit = create_habit(client, auth_headers)

        client.post(f"/habits/{habit['id']}/done/", headers=auth_headers)


        client.post(f"/habits/{habit['id']}/done/", headers=auth_headers)

        data = client.get("/dashboard/", headers=auth_headers).json()

        assert data["total_habits"] == 1
        assert data["completed_today"] == 1
        assert data["best_streak"] == 1


class TestBestStreak:
    def test_best_streak_multi_day(self, client, freeze_time, base_time):
        email = random_email()
        password = "123456"

        register_user(client, email, password)
        auth_headers = get_auth_headers(client, email, password)
        habit = create_habit(client, auth_headers)

        for i in range(3):
            with freeze_time(base_time - timedelta(days=i)):
                auth_headers = get_auth_headers(client, email, password)
                client.post(f"/habits/{habit['id']}/done/", headers=auth_headers)

        auth_headers = get_auth_headers(client, email, password)
        data = client.get("/dashboard/", headers=auth_headers).json()
        print(data)
        assert data["total_habits"] == 1
        assert data["best_streak"] == 3

    def test_best_streak_is_max_across_habits(self, client, auth_headers, freeze_time, base_time):
        email1 = random_email()
        email2 = random_email()
        password = "123456"

        register_user(client, email1, password)
        register_user(client, email2, password)

        auth_headers1 = get_auth_headers(client, email1, password)
        habit1 = create_habit(client, auth_headers1)
        client.post(f"/habits/{habit1['id']}/done/", headers=auth_headers1)

        auth_headers2 = get_auth_headers(client, email2, password)
        habit2 = create_habit(client, auth_headers2)

        for i in range(4):
            with freeze_time(base_time - timedelta(days=i)):
                auth_headers = get_auth_headers(client, email2, password)
                client.post(f"/habits/{habit2['id']}/done/", headers=auth_headers)

        auth_headers2 = get_auth_headers(client, email2, password)
        data = client.get("/dashboard/", headers=auth_headers2).json()
        print(data)
        assert data["total_habits"] == 1
        assert data["best_streak"] == 4

    def test_delete_habit_affects_best_streak(self, client, auth_headers):
        habit = create_habit(client, auth_headers)
        client.post(f"/habits/{habit['id']}/done/", headers=auth_headers)

        client.delete(f"/habits/{habit['id']}/done/", headers=auth_headers)

        data = client.get("/dashboard/", headers=auth_headers).json()

        assert data["total_habits"] == 1
        assert data["completed_today"] == 0
        assert data["best_streak"] == 0



class TestTotalHabits:
    def test_deleted_habit_not_counted(self, client, auth_headers):
        habits = [create_habit(client, auth_headers) for _ in range(4)]

        client.delete(f"/habits/{habits[0]['id']}/", headers=auth_headers)

        data = client.get("/dashboard/", headers=auth_headers).json()

        assert data["total_habits"] == 3
