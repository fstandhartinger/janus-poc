import asyncio
from typing import Optional

import httpx

from scoring_service.settings import get_settings


settings = get_settings()


async def start_container_in_sandbox(
    container_image: str,
    timeout_seconds: int = 300,
) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.sandy_api_url}/sandboxes",
            json={
                "image": container_image,
                "ports": [8080],
                "timeout_seconds": timeout_seconds,
                "resources": {
                    "cpu": "2",
                    "memory": "4Gi",
                    "gpu": True,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

        sandbox_id = data["sandbox_id"]
        return f"http://{sandbox_id}.sandbox.janus.rodeo:8080"


async def cleanup_sandbox(sandbox_url: str) -> None:
    sandbox_id = sandbox_url.split("//")[1].split(".")[0]

    async with httpx.AsyncClient(timeout=30) as client:
        await client.delete(f"{settings.sandy_api_url}/sandboxes/{sandbox_id}")


async def health_check_sandbox(sandbox_url: str, max_retries: int = 30) -> bool:
    async with httpx.AsyncClient(timeout=5) as client:
        for _ in range(max_retries):
            try:
                response = await client.get(f"{sandbox_url}/health")
                if response.status_code == 200:
                    return True
            except httpx.RequestError:
                pass
            await asyncio.sleep(1)

    return False
