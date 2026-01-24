"""Sandy sandbox management client for Janus agents."""

from __future__ import annotations

import atexit
import asyncio
import base64
import os
import threading
import time
from collections import deque
from dataclasses import dataclass

import httpx

_MAX_TTL_SECONDS = 3600
_MAX_CREATIONS_PER_HOUR = 10
_DEFAULT_MAX_SANDBOXES = 5
_DEFAULT_TTL_SECONDS = 600

_creation_timestamps: deque[float] = deque()
_active_sandboxes: dict[str, tuple[str, str | None]] = {}
_registry_lock = threading.Lock()


def _read_int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _default_ttl() -> int:
    return _read_int_env("JANUS_DEFAULT_SANDBOX_TTL", _DEFAULT_TTL_SECONDS)


def _max_active_sandboxes() -> int:
    return _read_int_env("JANUS_MAX_CHILD_SANDBOXES", _DEFAULT_MAX_SANDBOXES)


@dataclass
class Sandbox:
    """Represents a Sandy sandbox."""

    id: str
    public_url: str
    status: str
    ttl_remaining: int


class SandyClient:
    """Client for managing Sandy sandboxes."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url or os.environ.get("SANDY_BASE_URL")
        self.api_key = api_key or os.environ.get("SANDY_API_KEY")

        if not self.base_url:
            raise ValueError("SANDY_BASE_URL not configured")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _enforce_limits(self) -> None:
        now = time.time()
        cutoff = now - 3600
        max_active = _max_active_sandboxes()
        with _registry_lock:
            while _creation_timestamps and _creation_timestamps[0] < cutoff:
                _creation_timestamps.popleft()
            if len(_creation_timestamps) >= _MAX_CREATIONS_PER_HOUR:
                raise RuntimeError("Sandbox creation rate limit exceeded.")
            if len(_active_sandboxes) >= max_active:
                raise RuntimeError("Active sandbox limit exceeded.")

    async def _register_sandbox(self, sandbox_id: str) -> None:
        with _registry_lock:
            _creation_timestamps.append(time.time())
            _active_sandboxes[sandbox_id] = (self.base_url, self.api_key)

    async def _unregister_sandbox(self, sandbox_id: str) -> None:
        with _registry_lock:
            _active_sandboxes.pop(sandbox_id, None)

    async def create_sandbox(
        self,
        ttl_seconds: int | None = None,
        expose_ports: list[int] | None = None,
        priority: str = "NORMAL",
    ) -> Sandbox:
        """
        Create a new sandbox.

        Args:
            ttl_seconds: Time to live (default 10 minutes)
            expose_ports: Ports to expose publicly (e.g., [3000, 8080])
            priority: NORMAL or HIGH

        Returns:
            Sandbox object with id and public_url
        """
        await self._enforce_limits()
        ttl_seconds = ttl_seconds if ttl_seconds is not None else _default_ttl()
        if ttl_seconds <= 0:
            ttl_seconds = _default_ttl()
        if ttl_seconds > _MAX_TTL_SECONDS:
            ttl_seconds = _MAX_TTL_SECONDS

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/sandboxes",
                json={
                    "ttl_seconds": ttl_seconds,
                    "expose_ports": expose_ports or [],
                    "priority": priority,
                },
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

            sandbox_id = data.get("sandbox_id") or data.get("id")
            if not sandbox_id:
                raise RuntimeError("Sandbox ID missing from response.")

            await self._register_sandbox(str(sandbox_id))

            return Sandbox(
                id=str(sandbox_id),
                public_url=data.get("public_url", ""),
                status=data.get("status", "running"),
                ttl_remaining=int(data.get("ttl_remaining") or ttl_seconds),
            )

    async def exec_command(
        self,
        sandbox_id: str,
        command: str,
        timeout: int = 300,
        stream: bool = False,
    ) -> tuple[str, str, int]:
        """
        Execute a command in a sandbox.

        Args:
            sandbox_id: Target sandbox ID
            command: Shell command to run
            timeout: Execution timeout in seconds
            stream: If True, yield output chunks

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        async with httpx.AsyncClient(timeout=timeout + 10) as client:
            response = await client.post(
                f"{self.base_url}/api/sandboxes/{sandbox_id}/exec",
                json={
                    "command": command,
                    "timeout": timeout,
                },
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

            return (
                data.get("stdout", ""),
                data.get("stderr", ""),
                data.get("exit_code", -1),
            )

    async def write_file(
        self,
        sandbox_id: str,
        path: str,
        content: str | bytes,
    ) -> None:
        """Write a file to a sandbox."""
        if isinstance(content, str):
            content = content.encode("utf-8")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/sandboxes/{sandbox_id}/files/write",
                json={
                    "path": path,
                    "content": base64.b64encode(content).decode("utf-8"),
                    "encoding": "base64",
                },
                headers=self._headers(),
            )
            response.raise_for_status()

    async def read_file(
        self,
        sandbox_id: str,
        path: str,
    ) -> bytes:
        """Read a file from a sandbox."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/api/sandboxes/{sandbox_id}/files/read",
                params={"path": path},
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.content

    async def terminate(self, sandbox_id: str) -> None:
        """Terminate a sandbox."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/sandboxes/{sandbox_id}/terminate",
                headers=self._headers(),
            )
            response.raise_for_status()
        await self._unregister_sandbox(sandbox_id)

    async def get_status(self, sandbox_id: str) -> Sandbox:
        """Get sandbox status."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/api/sandboxes/{sandbox_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

            return Sandbox(
                id=sandbox_id,
                public_url=data.get("public_url", ""),
                status=data.get("status", "unknown"),
                ttl_remaining=int(data.get("ttl_remaining", 0)),
            )


async def _cleanup_active_sandboxes() -> None:
    with _registry_lock:
        items = list(_active_sandboxes.items())
    if not items:
        return

    async with httpx.AsyncClient(timeout=30) as client:
        for sandbox_id, (base_url, api_key) in items:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            try:
                await client.post(
                    f"{base_url}/api/sandboxes/{sandbox_id}/terminate",
                    headers=headers,
                )
            except Exception:
                continue
            with _registry_lock:
                _active_sandboxes.pop(sandbox_id, None)


def _run_cleanup() -> None:
    if not _active_sandboxes:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_cleanup_active_sandboxes())
    else:
        loop.create_task(_cleanup_active_sandboxes())


atexit.register(_run_cleanup)


# Convenience functions for common patterns

async def create_webapp_sandbox(
    port: int = 3000,
    ttl_minutes: int = 30,
) -> Sandbox:
    """
    Create a sandbox configured for hosting a web application.

    Returns sandbox with public URL for accessing the app.
    """
    client = SandyClient()
    return await client.create_sandbox(
        ttl_seconds=ttl_minutes * 60,
        expose_ports=[port],
    )


async def run_isolated_task(
    script: str,
    language: str = "python",
    timeout: int = 300,
) -> tuple[str, str, int]:
    """
    Run a script in an isolated sandbox.

    Creates sandbox, runs script, terminates sandbox.
    """
    client = SandyClient()

    sandbox = await client.create_sandbox(ttl_seconds=timeout + 60)

    try:
        ext = {"python": "py", "node": "js", "bash": "sh"}.get(language, "txt")
        script_path = f"/workspace/task.{ext}"
        await client.write_file(sandbox.id, script_path, script)

        cmd = {
            "python": f"python3 {script_path}",
            "node": f"node {script_path}",
            "bash": f"bash {script_path}",
        }.get(language, f"cat {script_path}")

        return await client.exec_command(sandbox.id, cmd, timeout=timeout)

    finally:
        await client.terminate(sandbox.id)
