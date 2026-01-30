"""Resilience and timeout integration tests.

Tests timeout handling and error recovery.
"""

import httpx
import pytest

from tests.config import config
from tests.utils import pre_release_headers


def get_headers():
    """Get headers including pre-release auth if configured."""
    return pre_release_headers() or {}


class TestTimeouts:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_gateway_responds_within_health_timeout(self):
        """Gateway health responds quickly."""
        gateway_url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
            # Should not timeout
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_streaming_stays_open_long_requests(self):
        """Streaming connection stays open for long agent tasks."""
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.complex_request_timeout, headers=get_headers()) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Write a short poem"}],
                    "stream": True,
                },
            ) as response:
                # Should be able to read the stream without timeout
                chunks = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunks.append(line)
                        if "[DONE]" in line:
                            break

                assert len(chunks) > 0


class TestRetryBehavior:
    """Test retry and fallback behavior."""

    @pytest.mark.asyncio
    async def test_invalid_competitor_returns_error(self):
        """Invalid competitor selection handles gracefully (error or fallback)."""
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "invalid-competitor-xyz",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                },
            )
            # Should get error (400/404), fallback (200), or not a 500
            assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_baseline_cli_stays_healthy_after_error(self):
        """Baseline CLI stays healthy after handling an error."""
        baseline_url = config.get_url("baseline_cli", "deployed")

        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
            # First, cause an error (empty messages)
            await client.post(
                f"{baseline_url}/v1/chat/completions",
                json={"model": "baseline", "messages": []},
            )

            # Then verify health is still good
            response = await client.get(f"{baseline_url}/health")
            assert response.status_code == 200


class TestConnectionResilience:
    """Test connection resilience."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self):
        """Service handles multiple sequential requests."""
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            for i in range(3):
                response = await client.post(
                    f"{gateway_url}/v1/chat/completions",
                    json={
                        "model": "baseline-cli-agent",
                        "messages": [{"role": "user", "content": f"Say {i}"}],
                        "stream": False,
                    },
                )
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Service handles concurrent requests."""
        import asyncio

        gateway_url = config.get_url("gateway", "deployed")

        async def make_request(n: int):
            async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
                response = await client.post(
                    f"{gateway_url}/v1/chat/completions",
                    json={
                        "model": "baseline-cli-agent",
                        "messages": [{"role": "user", "content": f"Say {n}"}],
                        "stream": False,
                    },
                )
                return response.status_code

        # Run 3 concurrent requests
        results = await asyncio.gather(
            make_request(1), make_request(2), make_request(3), return_exceptions=True
        )

        # All should succeed
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Request failed: {result}")
            assert result == 200


class TestErrorRecovery:
    """Test error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_malformed_request_doesnt_crash(self):
        """Malformed requests don't crash the service."""
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
            # Send malformed request
            await client.post(
                f"{gateway_url}/v1/chat/completions",
                content="not json",
                headers={**get_headers(), "Content-Type": "application/json"},
            )

            # Health should still be OK
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_large_message_handling(self):
        """Service handles large messages gracefully."""
        gateway_url = config.get_url("gateway", "deployed")

        # Create a reasonably large message (10KB)
        large_message = "Hello " * 2000

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": large_message}],
                    "stream": False,
                },
            )
            # Should either succeed or return a reasonable error
            assert response.status_code in [200, 400, 413, 422]
