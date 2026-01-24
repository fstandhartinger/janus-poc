"""Sandy sandbox runner for competitor containers."""

import asyncio
from typing import Any, AsyncIterator, Optional

import httpx


class SandyCompetitorRunner:
    """Run competitor containers inside Sandy sandboxes."""

    def __init__(
        self,
        sandy_base_url: str,
        competitor_image: str,
        api_key: str,
        competitor_port: int = 8080,
    ) -> None:
        self.sandy_base_url = sandy_base_url.rstrip("/")
        self.competitor_image = competitor_image
        self.api_key = api_key
        self.competitor_port = competitor_port
        self.sandbox_id: Optional[str] = None

    async def start_sandbox(self) -> str:
        """Create a Sandy sandbox and start the competitor container."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.sandy_base_url}/api/sandboxes",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "image": "sandy-docker",
                    "resources": {
                        "cpu": 2,
                        "memory_mb": 4096,
                        "disk_gb": 10,
                    },
                    "env": {
                        "CHUTES_API_KEY": self.api_key,
                    },
                },
            )
            response.raise_for_status()
            self.sandbox_id = response.json()["sandbox_id"]

            exec_response = await client.post(
                f"{self.sandy_base_url}/api/sandboxes/{self.sandbox_id}/exec",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "command": (
                        "docker pull "
                        f"{self.competitor_image} && "
                        "docker run -d -p "
                        f"{self.competitor_port}:{self.competitor_port} "
                        "--name competitor "
                        f"{self.competitor_image}"
                    )
                },
            )
            exec_response.raise_for_status()

            await self._wait_for_ready()

            return self.sandbox_id

    async def _wait_for_ready(self, timeout: int = 30) -> None:
        """Wait for the competitor container to be ready."""
        if not self.sandbox_id:
            raise RuntimeError("Sandbox ID not set")

        start = asyncio.get_running_loop().time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            while asyncio.get_running_loop().time() - start < timeout:
                try:
                    response = await client.post(
                        f"{self.sandy_base_url}/api/sandboxes/{self.sandbox_id}/exec",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "command": (
                                "curl -s "
                                f"http://localhost:{self.competitor_port}/health"
                            )
                        },
                    )
                    response.raise_for_status()
                    result = response.json()
                    stdout = result.get("stdout", "")
                    if result.get("exit_code") == 0 and "ok" in stdout.lower():
                        return
                except (httpx.HTTPError, ValueError, KeyError):
                    pass
                await asyncio.sleep(1)

        raise TimeoutError("Competitor container failed to start")

    async def forward_request(self, request: dict[str, Any]) -> AsyncIterator[str]:
        """Forward a chat completion request to the competitor container."""
        if not self.sandbox_id:
            raise RuntimeError("Sandbox ID not set")

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                (
                    f"{self.sandy_base_url}/api/sandboxes/"
                    f"{self.sandbox_id}/proxy/{self.competitor_port}/"
                    "v1/chat/completions"
                ),
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=request,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    yield line

    async def stop_sandbox(self) -> None:
        """Terminate the sandbox."""
        if not self.sandbox_id:
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{self.sandy_base_url}/api/sandboxes/{self.sandbox_id}/terminate",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        self.sandbox_id = None
