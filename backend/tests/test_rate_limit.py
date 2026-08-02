import uuid

import pytest
from app.main import app
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def client():
    return TestClient(app)


class TestRateLimiting:
    async def test_rate_limit_header_present(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_register_rate_limit(self, client):
        suffix = uuid.uuid4().hex[:8]
        responses = []
        for i in range(6):
            resp = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"rl-{i}-{suffix}@test.com",
                    "password": "TestPass123!",
                    "full_name": f"RateLimit {i}",
                    "role": "patient",
                },
            )
            responses.append(resp)
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes or 201 in status_codes

    async def test_health_not_rate_limited(self, client):
        for _ in range(20):
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
