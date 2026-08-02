import pytest
from app.core.security import create_access_token
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_auth():
    from app.core.deps import get_current_user, require_role

    app = FastAPI()

    @app.get("/me")
    async def me(current_user: dict = Depends(get_current_user)):
        return {"user_id": current_user["sub"], "role": current_user["role"]}

    @app.get("/admin-only")
    async def admin_only(current_user: dict = Depends(require_role("admin"))):
        return {"admin": True}

    @app.get("/doctor-or-admin")
    async def multi_role(current_user: dict = Depends(require_role("doctor", "admin"))):
        return {"allowed": True}

    return app


@pytest.fixture
def client(app_with_auth):
    return TestClient(app_with_auth)


class TestGetCurrentUser:
    def test_valid_token(self, client):
        token = create_access_token("user-1", "patient")
        response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json() == {"user_id": "user-1", "role": "patient"}

    def test_missing_header(self, client):
        response = client.get("/me")
        assert response.status_code == 401

    def test_invalid_scheme(self, client):
        response = client.get("/me", headers={"Authorization": "Basic xyz"})
        assert response.status_code == 401

    def test_malformed_token(self, client):
        response = client.get("/me", headers={"Authorization": "Bearer garbage"})
        assert response.status_code == 401

    def test_expired_token(self, client):
        from datetime import UTC, datetime
        from unittest.mock import patch

        with patch("app.core.security.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, tzinfo=UTC)
            expired = create_access_token("user-1", "patient")

        response = client.get("/me", headers={"Authorization": f"Bearer {expired}"})
        assert response.status_code == 401


class TestRequireRole:
    def test_allowed_role(self, client):
        token = create_access_token("user-1", "admin")
        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    def test_wrong_role(self, client):
        token = create_access_token("user-1", "patient")
        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_multi_role(self, client):
        token = create_access_token("user-1", "doctor")
        response = client.get("/doctor-or-admin", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
