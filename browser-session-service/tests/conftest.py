"""Pytest configuration and fixtures."""

import os
from typing import AsyncGenerator, Generator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# Test encryption secret (32 bytes base64-encoded, exactly 32 bytes when decoded)
# base64.b64encode(b'test_secret_12345678901234567890').decode() = 'dGVzdF9zZWNyZXRfMTIzNDU2Nzg5MDEyMzQ1Njc4OTA='
TEST_ENCRYPTION_SECRET = "dGVzdF9zZWNyZXRfMTIzNDU2Nzg5MDEyMzQ1Njc4OTA="


# Set environment variables before any other imports
_test_env = {
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "SESSION_ENCRYPTION_SECRET": TEST_ENCRYPTION_SECRET,
    "CHUTES_IDP_JWKS_URL": "https://test.idp/.well-known/jwks.json",
    "CHUTES_IDP_ISSUER": "https://test.idp",
    "CHUTES_IDP_AUDIENCE": "janus",
    "SESSION_INIT_DB": "true",
    "SESSION_DEBUG": "true",
}
os.environ.update(_test_env)


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    # Import here to ensure env vars are set
    from browser_session_service.config import get_settings
    from browser_session_service.database import Base

    get_settings.cache_clear()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with mocked auth."""
    # Import here to ensure env vars are set
    from browser_session_service.config import get_settings
    from browser_session_service.main import app
    from browser_session_service import auth
    from browser_session_service.database import get_session

    get_settings.cache_clear()

    # Override database session
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    # Mock auth to always return a test user
    def mock_get_current_user_id() -> str:
        return "test-user-123"

    app.dependency_overrides[auth.get_current_user_id] = mock_get_current_user_id

    # Create client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def sample_storage_state() -> dict:
    """Sample Playwright storage state for testing."""
    return {
        "cookies": [
            {
                "name": "session_id",
                "value": "abc123def456",
                "domain": ".example.com",
                "path": "/",
                "expires": 1735689600,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
            {
                "name": "auth_token",
                "value": "xyz789",
                "domain": ".example.com",
                "path": "/api",
                "expires": -1,
                "httpOnly": False,
                "secure": True,
                "sameSite": "Strict",
            },
        ],
        "origins": [
            {
                "origin": "https://example.com",
                "localStorage": [
                    {"name": "user_preferences", "value": '{"theme":"dark"}'},
                    {"name": "auth_token", "value": "bearer_xyz789"},
                ],
            }
        ],
    }
