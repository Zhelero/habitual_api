from starlette.testclient import TestClient


def test_middleware_exception(client, caplog):
    app = client.app

    @app.get("/error")
    def error():
        raise RuntimeError()

    test_client = TestClient(app, raise_server_exceptions=False)

    response = test_client.get("/error")

    assert response.status_code == 500
    assert "-> 500" in caplog.text
