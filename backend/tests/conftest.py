import os

# Disable rate limiting during tests
os.environ["DISABLE_RATE_LIMIT"] = "true"

import pytest
import pytest_asyncio
from app.core import database as app_db
from app.core.config import settings
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Replace app engine with NullPool engine for tests to prevent connection sharing
_app_test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
app_db._engine = _app_test_engine
app_db._async_session_local = async_sessionmaker(
    _app_test_engine, class_=AsyncSession, expire_on_commit=False
)

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    yield engine
    await _app_test_engine.dispose()
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    async with test_engine.connect() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()
