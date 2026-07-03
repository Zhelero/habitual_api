import logging

from fastapi.testclient import TestClient

from app.main import app


def test_startup_logs(caplog):
    with caplog.at_level(logging.INFO, logger="app.main"):
        with TestClient(app):
            pass

    assert "Starting Habitual API" in caplog.text


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
