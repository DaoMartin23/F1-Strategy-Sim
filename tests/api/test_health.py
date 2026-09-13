from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_vite_dev_origin() -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin() -> None:
    response = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert response.headers.get("access-control-allow-origin") is None
