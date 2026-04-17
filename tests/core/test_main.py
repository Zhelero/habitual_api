def test_startup_logs(caplog):
    from app.main import startup

    startup()

    assert "Starting Habitual API" in caplog.text


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
