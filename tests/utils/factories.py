from tests.utils.helpers import random_habit_name


def create_habit(client, headers, name=None):
    res = client.post("/habits", json={
        "name": name or random_habit_name(),
    }, headers=headers)

    assert res.status_code == 201
    return res.json()
