from fastapi.testclient import TestClient


# --- Health endpoints ---
def test_health(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready(client: TestClient):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] in ("ready", "degraded")


def test_version(client: TestClient):
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "env" in data
    assert "commit" in data


# --- Error envelope ---
def test_404_returns_envelope(client: TestClient):
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "HTTP_404"


def test_405_returns_envelope(client: TestClient):
    response = client.post("/api/v1/health")
    assert response.status_code == 405
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "HTTP_405"


def test_validation_error_returns_envelope(client: TestClient):
    from app.core.exceptions import AppError
    from app.main import app

    @app.get("/test/app-error")
    async def trigger_error():
        raise AppError(code="TEST_ERROR", message="test", status_code=400)

    response = client.get("/test/app-error")
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "TEST_ERROR"


# --- SECURITY HEADERS ---
def test_security_headers(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "x-request-id" in response.headers


# --- Config ---
def test_config_defaults():
    from app.core.config import settings

    assert settings.ENV == "local"
    assert settings.is_production is False
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
