import importlib
import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

TEST_DB_PATH = Path(__file__).parent / "test_memory.db"


@pytest.fixture(scope="session", autouse=True)
def _configure_env() -> None:
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
    os.environ["MEMORY_INIT_DB"] = "true"
    os.environ["CHUTES_API_KEY"] = "test-key"
    os.environ["MEMORY_RATE_LIMIT_PER_MINUTE"] = "1000"


@pytest.fixture
async def client():
    import memory_service.config as config

    config.get_settings.cache_clear()

    import memory_service.database as database
    import memory_service.main as main

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    await database.init_db()
    await main.startup()
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    await main.shutdown()

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
