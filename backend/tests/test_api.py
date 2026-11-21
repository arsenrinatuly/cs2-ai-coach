from fastapi.testclient import TestClient

from backend.api import app


def test_health_and_api_docs() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert client.get("/docs").status_code == 200
        assert "/health" in client.get("/openapi.json").json()["paths"]
