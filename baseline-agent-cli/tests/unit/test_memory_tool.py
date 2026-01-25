"""Tests for the memory investigation tool."""

import httpx
import pytest

from janus_baseline_agent_cli.tools.memory import investigate_memory


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


@pytest.mark.asyncio
async def test_investigate_memory_formats_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse(
                {
                    "memories": [
                        {
                            "id": "mem_1",
                            "caption": "User likes pizza",
                            "created_at": "2025-01-01T00:00:00Z",
                            "full_text": "User mentioned loving pizza during onboarding.",
                        }
                    ]
                }
            )

    monkeypatch.setattr(
        "janus_baseline_agent_cli.tools.memory.httpx.AsyncClient",
        FakeClient,
    )

    output = await investigate_memory(
        memory_ids=["mem_1"],
        user_id="user-1",
        memory_service_url="https://memory.test",
        query="pizza preference",
    )

    assert "## Retrieved Memories" in output
    assert "*Investigating: pizza preference*" in output
    assert "[mem_1] User likes pizza" in output
    assert "User mentioned loving pizza" in output


@pytest.mark.asyncio
async def test_investigate_memory_handles_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse({"memories": []})

    monkeypatch.setattr(
        "janus_baseline_agent_cli.tools.memory.httpx.AsyncClient",
        FakeClient,
    )

    output = await investigate_memory(
        memory_ids=["mem_missing"],
        user_id="user-1",
        memory_service_url="https://memory.test",
    )

    assert output == "No memories found with the provided IDs."


@pytest.mark.asyncio
async def test_investigate_memory_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FailingClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, *args, **kwargs):
            raise httpx.RequestError("boom", request=None)

    monkeypatch.setattr(
        "janus_baseline_agent_cli.tools.memory.httpx.AsyncClient",
        FailingClient,
    )

    output = await investigate_memory(
        memory_ids=["mem_1"],
        user_id="user-1",
        memory_service_url="https://memory.test",
    )

    assert output.startswith("Error retrieving memories:")
