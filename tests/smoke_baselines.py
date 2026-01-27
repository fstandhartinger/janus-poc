"""
Smoke tests for baseline models via the gateway.

Usage:
    python tests/smoke_baselines.py [--gateway-url URL] [--baseline MODEL]

Examples:
    # Test against deployed gateway
    python tests/smoke_baselines.py

    # Test locally
    python tests/smoke_baselines.py --gateway-url http://localhost:8000

    # Test specific baseline
    python tests/smoke_baselines.py --baseline baseline-cli-agent
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from tests.utils import pre_release_headers
DEFAULT_GATEWAY_URL = "https://janus-gateway-bqou.onrender.com"
BASELINES = ["baseline-cli-agent", "baseline-langchain"]
BASELINE_ALIASES = {
    "baseline": "baseline-cli-agent",
    "baseline-cli": "baseline-cli-agent",
    "baseline-agent-cli": "baseline-cli-agent",
}


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: float


class SmokeTests:
    def __init__(self, gateway_url: str, baseline: Optional[str] = None):
        self.gateway_url = gateway_url.rstrip("/")
        self.explicit_baseline = baseline is not None
        normalized = self._normalize_baseline(baseline) if baseline else None
        self.baselines = [normalized] if normalized else list(BASELINES)
        self.results: list[TestResult] = []
        self.headers = pre_release_headers() or None

    def _normalize_baseline(self, baseline: str | None) -> str | None:
        if not baseline:
            return None
        return BASELINE_ALIASES.get(baseline, baseline)

    async def run_all(self) -> bool:
        """Run all smoke tests and return True if all pass."""
        print(f"\n{'=' * 60}")
        print(f"Baseline Smoke Tests - Gateway: {self.gateway_url}")
        print(f"{'=' * 60}\n")

        await self.test_gateway_health()

        available_models = await self.fetch_available_models()
        baselines = self._resolve_baselines(available_models)
        if not baselines:
            self.record("baselines_available", False, "No baseline models available", 0)
            self.print_summary()
            return False

        for baseline in baselines:
            print(f"\n--- Testing: {baseline} ---\n")
            await self.test_simple_query(baseline)
            await self.test_streaming(baseline)
            await self.test_math_question(baseline)
            await self.test_empty_message(baseline)

        self.print_summary()
        return all(result.passed for result in self.results)

    async def fetch_available_models(self) -> set[str] | None:
        """Fetch available model IDs from the gateway."""
        try:
            async with httpx.AsyncClient(timeout=10, headers=self.headers) as client:
                response = await client.get(f"{self.gateway_url}/v1/models")
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return None

        models = {
            item.get("id")
            for item in payload.get("data", [])
            if isinstance(item, dict) and item.get("id")
        }
        return {model for model in models if model}

    def _resolve_baselines(self, available_models: set[str] | None) -> list[str]:
        if available_models is None:
            return self.baselines

        if self.explicit_baseline:
            baseline = self.baselines[0]
            if baseline not in available_models:
                self.record(
                    f"{baseline}_available",
                    False,
                    "Baseline not listed in /v1/models",
                    0,
                )
                return []
            return [baseline]

        selected = []
        for baseline in self.baselines:
            if baseline in available_models:
                selected.append(baseline)
            else:
                self.record(
                    f"{baseline}_available",
                    True,
                    "Skipped (not listed in /v1/models)",
                    0,
                )
        return selected

    def record(self, name: str, passed: bool, message: str, duration_ms: float) -> None:
        result = TestResult(name, passed, message, duration_ms)
        self.results.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {message} ({duration_ms:.0f}ms)")

    async def test_gateway_health(self) -> None:
        """Test gateway health endpoint."""
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10, headers=self.headers) as client:
                response = await client.get(f"{self.gateway_url}/health")
                duration = (time.perf_counter() - start) * 1000
                if response.status_code == 200:
                    self.record("gateway_health", True, "Gateway healthy", duration)
                else:
                    self.record(
                        "gateway_health",
                        False,
                        f"Status {response.status_code}",
                        duration,
                    )
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            self.record("gateway_health", False, str(exc), duration)

    async def test_simple_query(self, baseline: str) -> None:
        """Test simple chat query."""
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60, headers=self.headers) as client:
                response = await client.post(
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": baseline,
                        "messages": [{"role": "user", "content": "What is 2+2?"}],
                        "stream": False,
                    },
                )
                duration = (time.perf_counter() - start) * 1000
                if response.status_code != 200:
                    self.record(
                        f"{baseline}_simple",
                        False,
                        f"Status {response.status_code}",
                        duration,
                    )
                    return

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if "error" in content.lower() and "sorry" in content.lower():
                    self.record(
                        f"{baseline}_simple",
                        False,
                        f"Error response: {content[:100]}",
                        duration,
                    )
                elif "4" in content:
                    self.record(f"{baseline}_simple", True, "Correct answer", duration)
                else:
                    self.record(
                        f"{baseline}_simple",
                        True,
                        f"Got response: {content[:50]}...",
                        duration,
                    )

        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            self.record(f"{baseline}_simple", False, str(exc), duration)

    async def test_streaming(self, baseline: str) -> None:
        """Test streaming response."""
        start = time.perf_counter()
        chunks = 0
        try:
            async with httpx.AsyncClient(timeout=60, headers=self.headers) as client:
                async with client.stream(
                    "POST",
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": baseline,
                        "messages": [{"role": "user", "content": "Say hello"}],
                        "stream": True,
                    },
                ) as response:
                    if response.status_code != 200:
                        duration = (time.perf_counter() - start) * 1000
                        self.record(
                            f"{baseline}_stream",
                            False,
                            f"Status {response.status_code}",
                            duration,
                        )
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line[6:] != "[DONE]":
                            chunks += 1

                duration = (time.perf_counter() - start) * 1000
                if chunks > 0:
                    self.record(
                        f"{baseline}_stream",
                        True,
                        f"{chunks} chunks received",
                        duration,
                    )
                else:
                    self.record(
                        f"{baseline}_stream",
                        False,
                        "No chunks received",
                        duration,
                    )

        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            self.record(f"{baseline}_stream", False, str(exc), duration)

    async def test_math_question(self, baseline: str) -> None:
        """Test a math/reasoning question."""
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60, headers=self.headers) as client:
                response = await client.post(
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": baseline,
                        "messages": [
                            {
                                "role": "user",
                                "content": "If I have 3 apples and buy 2 more, how many do I have?",
                            }
                        ],
                        "stream": False,
                    },
                )
                duration = (time.perf_counter() - start) * 1000
                if response.status_code != 200:
                    self.record(
                        f"{baseline}_math",
                        False,
                        f"Status {response.status_code}",
                        duration,
                    )
                    return

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                if "5" in content:
                    self.record(
                        f"{baseline}_math", True, "Correct answer (5)", duration
                    )
                elif "error" in content.lower():
                    self.record(f"{baseline}_math", False, "Error in response", duration)
                else:
                    self.record(f"{baseline}_math", True, "Response received", duration)

        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            self.record(f"{baseline}_math", False, str(exc), duration)

    async def test_empty_message(self, baseline: str) -> None:
        """Test handling of edge cases."""
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30, headers=self.headers) as client:
                response = await client.post(
                    f"{self.gateway_url}/v1/chat/completions",
                    json={
                        "model": baseline,
                        "messages": [{"role": "user", "content": ""}],
                        "stream": False,
                    },
                )
                duration = (time.perf_counter() - start) * 1000
                if response.status_code in [200, 400]:
                    self.record(
                        f"{baseline}_edge",
                        True,
                        f"Handled gracefully (status {response.status_code})",
                        duration,
                    )
                else:
                    self.record(
                        f"{baseline}_edge",
                        False,
                        f"Unexpected status {response.status_code}",
                        duration,
                    )

        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            self.record(f"{baseline}_edge", False, str(exc), duration)

    def print_summary(self) -> None:
        """Print test summary."""
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")

        passed = sum(1 for result in self.results if result.passed)
        failed = sum(1 for result in self.results if not result.passed)
        total = len(self.results)

        print(f"Passed: {passed}/{total}")
        print(f"Failed: {failed}/{total}")

        if failed > 0:
            print("\nFailed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.name}: {result.message}")

        print(f"\n{'=' * 60}\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline smoke tests via gateway")
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL, help="Gateway URL")
    parser.add_argument("--baseline", help="Specific baseline to test")
    args = parser.parse_args()

    tests = SmokeTests(args.gateway_url, args.baseline)
    success = await tests.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
