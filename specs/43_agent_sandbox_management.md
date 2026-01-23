# Spec 43: Agent Sandy Sandbox Management

## Status: DRAFT

## Context / Why

The agent runs inside a Sandy sandbox, but currently cannot create additional sandboxes for tasks like:

- Running isolated experiments
- Hosting web applications
- Running services that persist beyond the agent's task
- Parallel execution of independent tasks

The agent should be able to create, manage, and terminate Sandy sandboxes using the same authentication that started the original agent request.

## Goals

- Enable agent to create new Sandy sandboxes
- Pass through authentication from original request
- Provide sandbox management utilities to agent
- Support hosting public web applications
- Enable sandbox-to-sandbox communication

## Non-Goals

- Changing Sandy's core API
- Unlimited sandbox creation (rate limits apply)
- Long-term persistent sandboxes (TTL enforced)

## Functional Requirements

### FR-1: Authentication Pass-Through

The agent inherits the auth token from the original request:

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py

def _build_agent_env(self, request: ChatCompletionRequest, sandbox_id: str) -> dict:
    """Build environment including auth for child sandboxes."""
    settings = get_settings()

    # Extract bearer token from original request (if available)
    # This could come from the gateway headers or request context
    auth_token = getattr(request, '_auth_token', None) or settings.sandy_api_key

    return {
        # ... existing vars ...

        # Sandy API access for child sandboxes
        "SANDY_API_KEY": auth_token,
        "SANDY_BASE_URL": settings.sandy_base_url,

        # Quotas (informational)
        "JANUS_MAX_CHILD_SANDBOXES": "5",
        "JANUS_DEFAULT_SANDBOX_TTL": "600",  # 10 minutes
    }
```

### FR-2: Sandy Client Library for Agent

Provide a Python library the agent can use:

```python
# agent-pack/lib/sandy_client.py
"""Sandy sandbox management client for Janus agents."""

import os
import json
import httpx
from typing import Optional, AsyncIterator
from dataclasses import dataclass


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
        base_url: str = None,
        api_key: str = None,
    ):
        self.base_url = base_url or os.environ.get("SANDY_BASE_URL")
        self.api_key = api_key or os.environ.get("SANDY_API_KEY")

        if not self.base_url:
            raise ValueError("SANDY_BASE_URL not configured")

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def create_sandbox(
        self,
        ttl_seconds: int = 600,
        expose_ports: list[int] = None,
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

            return Sandbox(
                id=data.get("sandbox_id") or data.get("id"),
                public_url=data.get("public_url", ""),
                status="running",
                ttl_remaining=ttl_seconds,
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
        import base64

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
                ttl_remaining=data.get("ttl_remaining", 0),
            )


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

    # Create sandbox
    sandbox = await client.create_sandbox(ttl_seconds=timeout + 60)

    try:
        # Write script
        ext = {"python": "py", "node": "js", "bash": "sh"}.get(language, "txt")
        script_path = f"/workspace/task.{ext}"
        await client.write_file(sandbox.id, script_path, script)

        # Execute
        cmd = {
            "python": f"python3 {script_path}",
            "node": f"node {script_path}",
            "bash": f"bash {script_path}",
        }.get(language, f"cat {script_path}")

        return await client.exec_command(sandbox.id, cmd, timeout=timeout)

    finally:
        await client.terminate(sandbox.id)
```

### FR-3: Web Application Hosting

Enable hosting public web applications:

```python
# agent-pack/lib/webapp_host.py
"""Host web applications on Sandy sandboxes."""

import asyncio
from .sandy_client import SandyClient, Sandbox


async def deploy_webapp(
    files: dict[str, str],
    start_command: str,
    port: int = 3000,
    ttl_minutes: int = 30,
    install_command: str = None,
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

    Example:
        sandbox, url = await deploy_webapp(
            files={
                "/workspace/app/index.js": "const express = require('express')...",
                "/workspace/app/package.json": '{"dependencies": {...}}',
            },
            install_command="cd /workspace/app && npm install",
            start_command="cd /workspace/app && node index.js",
            port=3000,
        )
        print(f"App running at: {url}")
    """
    client = SandyClient()

    # Create sandbox with exposed port
    sandbox = await client.create_sandbox(
        ttl_seconds=ttl_minutes * 60,
        expose_ports=[port],
    )

    try:
        # Write all files
        for path, content in files.items():
            await client.write_file(sandbox.id, path, content)

        # Run install command if provided
        if install_command:
            stdout, stderr, code = await client.exec_command(
                sandbox.id,
                install_command,
                timeout=120,
            )
            if code != 0:
                raise RuntimeError(f"Install failed: {stderr}")

        # Start the app in background
        await client.exec_command(
            sandbox.id,
            f"nohup {start_command} > /tmp/app.log 2>&1 &",
            timeout=10,
        )

        # Wait for app to be ready
        await asyncio.sleep(2)

        # Construct public URL
        public_url = f"{sandbox.public_url}:{port}"

        return sandbox, public_url

    except Exception as e:
        await client.terminate(sandbox.id)
        raise


# Example usage in agent prompt:
"""
## Hosting a Web App

You can deploy web applications that users can access:

```python
from lib.webapp_host import deploy_webapp

# Deploy a simple Express app
sandbox, url = await deploy_webapp(
    files={
        "/workspace/app/index.js": '''
const express = require("express");
const app = express();
app.get("/", (req, res) => res.send("Hello from Janus!"));
app.listen(3000);
''',
        "/workspace/app/package.json": '{"dependencies":{"express":"^4.18.0"}}',
    },
    install_command="cd /workspace/app && npm install",
    start_command="cd /workspace/app && node index.js",
    port=3000,
    ttl_minutes=30,
)

print(f"Your app is live at: {url}")
```
"""
```

### FR-4: System Prompt Addition

Add sandbox management to the system prompt:

```markdown
### 🖥️ Sandbox Management

You can create and manage additional sandboxes for:
- Running isolated experiments
- Hosting web applications
- Running persistent services

```python
from lib.sandy_client import SandyClient, create_webapp_sandbox, run_isolated_task

# Create a new sandbox
client = SandyClient()
sandbox = await client.create_sandbox(ttl_seconds=600, expose_ports=[3000])
print(f"Sandbox URL: {sandbox.public_url}")

# Run isolated task
stdout, stderr, code = await run_isolated_task(
    script="print('Hello from isolated sandbox!')",
    language="python",
)

# Host a web app
from lib.webapp_host import deploy_webapp
sandbox, url = await deploy_webapp(
    files={...},
    start_command="python app.py",
    port=5000,
)
print(f"App live at: {url}")
```
```

## Non-Functional Requirements

### NFR-1: Rate Limiting

- Max 5 concurrent child sandboxes per agent
- Max 10 sandbox creations per hour
- Enforce TTL (max 1 hour for child sandboxes)

### NFR-2: Resource Isolation

- Child sandboxes have same resource limits as parent
- Network isolation between sandboxes (unless explicitly connected)
- Storage isolation (each sandbox has own filesystem)

### NFR-3: Cleanup

- Parent sandbox termination cascades to children
- Orphan detection for abandoned sandboxes
- Automatic TTL enforcement

## Acceptance Criteria

- [ ] Agent can create child sandboxes
- [ ] Auth token passed through correctly
- [ ] Sandy client library available to agent
- [ ] Web app hosting works
- [ ] Public URLs accessible
- [ ] Rate limits enforced
- [ ] Cleanup on parent termination

## Files to Create/Modify

```
baseline-agent-cli/
├── agent-pack/
│   └── lib/
│       ├── sandy_client.py    # NEW - Sandy API client
│       └── webapp_host.py     # NEW - Web app deployment
├── janus_baseline_agent_cli/
│   ├── prompts/
│   │   └── system.md          # MODIFY - Add sandbox docs
│   └── services/
│       └── sandy.py           # MODIFY - Pass auth token
```

## Related Specs

- `specs/41_enhanced_agent_system_prompt.md` - Agent capabilities
- `specs/42_sandbox_file_serving.md` - File serving
- `specs/08_sandy_integration.md` - Original Sandy spec
