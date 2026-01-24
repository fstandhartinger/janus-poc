"""Host web applications on Sandy sandboxes."""

from __future__ import annotations

import asyncio

from .sandy_client import SandyClient, Sandbox


async def deploy_webapp(
    files: dict[str, str],
    start_command: str,
    port: int = 3000,
    ttl_minutes: int = 30,
    install_command: str | None = None,
) -> tuple[Sandbox, str]:
    """
    Deploy a web application to a sandbox.

    Args:
        files: Dict of {filepath: content} to write
        start_command: Command to start the app (e.g., "npm start")
        port: Port the app listens on
        ttl_minutes: How long sandbox lives
        install_command: Optional setup command (e.g., "npm install")

    Returns:
        Tuple of (Sandbox, public_url)
    """
    client = SandyClient()

    sandbox = await client.create_sandbox(
        ttl_seconds=ttl_minutes * 60,
        expose_ports=[port],
    )

    try:
        for path, content in files.items():
            await client.write_file(sandbox.id, path, content)

        if install_command:
            _, stderr, code = await client.exec_command(
                sandbox.id,
                install_command,
                timeout=120,
            )
            if code != 0:
                raise RuntimeError(f"Install failed: {stderr}")

        await client.exec_command(
            sandbox.id,
            f"nohup {start_command} > /tmp/app.log 2>&1 &",
            timeout=10,
        )

        await asyncio.sleep(2)

        public_url = (
            f"{sandbox.public_url}:{port}" if sandbox.public_url else ""
        )

        return sandbox, public_url

    except Exception:
        await client.terminate(sandbox.id)
        raise
