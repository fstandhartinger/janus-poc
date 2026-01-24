import importlib
import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

TEST_DB_PATH = Path(__file__).parent / "test_scoring.db"


@pytest.fixture(scope="session", autouse=True)
def _configure_env() -> None:
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
    os.environ["SCORING_INIT_DB"] = "true"
    os.environ["SCORING_SSE_POLL_INTERVAL"] = "0.01"
    os.environ["SCORING_MAX_CONCURRENT_RUNS"] = "0"


@pytest.fixture
async def client():
    import scoring_service.settings as settings

    settings.get_settings.cache_clear()

    import scoring_service.database as database
    importlib.reload(database)

    import scoring_service.executor as executor
    importlib.reload(executor)

    import scoring_service.main as main
    importlib.reload(main)

    await main.startup()
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    await main.shutdown()

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
