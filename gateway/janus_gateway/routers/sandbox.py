"""Sandbox API router for session capture workflows."""

import json
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from janus_gateway.config import get_settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

settings = get_settings()


class CreateSandboxRequest(BaseModel):
    """Request to create a sandbox for session capture."""

    flavor: str = "agent-ready"
    enableVnc: bool = True
    timeout: int = 600


class CreateSandboxResponse(BaseModel):
    """Response after creating a sandbox."""

    id: str
    url: str
    vncPort: int


class CaptureSessionResponse(BaseModel):
    """Response after capturing browser session state."""

    storage_state: dict[str, Any]
    detected_domains: list[str]


def _get_sandy_config() -> tuple[str, str]:
    """Get Sandy base URL and API key, raising if not configured."""
    if not settings.sandy_base_url:
        raise HTTPException(
            status_code=503,
            detail="Sandy service not configured. Set SANDY_BASE_URL environment variable.",
        )
    if not settings.sandy_api_key:
        raise HTTPException(
            status_code=503,
            detail="Sandy API key not configured. Set SANDY_API_KEY environment variable.",
        )
    return settings.sandy_base_url.rstrip("/"), settings.sandy_api_key


@router.post("/create", response_model=CreateSandboxResponse)
async def create_sandbox(request: CreateSandboxRequest) -> CreateSandboxResponse:
    """Create a sandbox for browser session capture.

    This endpoint creates a Sandy sandbox with VNC enabled for
    interactive browser session capture.
    """
    sandy_url, api_key = _get_sandy_config()

    logger.info(
        "sandbox_create_request",
        flavor=request.flavor,
        enable_vnc=request.enableVnc,
        timeout=request.timeout,
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{sandy_url}/api/sandboxes",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "image": request.flavor,
                    "enableVnc": request.enableVnc,
                    "timeout": request.timeout,
                    "resources": {
                        "cpu": 2,
                        "memory_mb": 4096,
                        "disk_gb": 10,
                    },
                },
            )

            if response.status_code != 200:
                logger.error(
                    "sandbox_create_failed",
                    status=response.status_code,
                    detail=response.text,
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text or "Failed to create sandbox",
                )

            data = response.json()
            # Sandy returns sandboxId (camelCase), not sandbox_id
            sandbox_id = data.get("sandboxId") or data.get("sandbox_id") or data.get("id")
            if not sandbox_id:
                raise HTTPException(
                    status_code=500,
                    detail="Sandy response missing sandbox_id",
                )

            # Construct VNC URL from Sandy base URL (handle both camelCase and snake_case)
            vnc_port = data.get("vncPort") or data.get("vnc_port") or 5900

            logger.info("sandbox_created", sandbox_id=sandbox_id, vnc_port=vnc_port)

            return CreateSandboxResponse(
                id=sandbox_id,
                url=sandy_url,
                vncPort=vnc_port,
            )

    except httpx.RequestError as e:
        logger.error("sandbox_create_network_error", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Sandy service: {e}",
        ) from e


@router.post("/{sandbox_id}/capture-session", response_model=CaptureSessionResponse)
async def capture_session(sandbox_id: str) -> CaptureSessionResponse:
    """Capture browser session state from a sandbox.

    Executes a command in the sandbox to export cookies, localStorage,
    and other browser state that can be used to restore the session.
    """
    sandy_url, api_key = _get_sandy_config()

    logger.info("sandbox_capture_session", sandbox_id=sandbox_id)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Execute session capture script in sandbox
            # This uses agent-browser or Playwright to export storage state
            capture_script = """
import json
import subprocess
import sys

try:
    # Try using agent-browser if available
    result = subprocess.run(
        ['agent-browser', 'eval', 'JSON.stringify(await context.storageState())'],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode == 0:
        print(result.stdout)
        sys.exit(0)
except Exception:
    pass

# Fallback: use Playwright directly
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        # Connect to existing browser if possible
        browser = p.chromium.launch()
        context = browser.new_context()
        state = context.storage_state()
        print(json.dumps(state))
        browser.close()
except Exception as e:
    # Return empty state as fallback
    print(json.dumps({'cookies': [], 'origins': []}))
"""

            response = await client.post(
                f"{sandy_url}/api/sandboxes/{sandbox_id}/exec",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "command": f"python3 -c {repr(capture_script)}",
                },
            )

            if response.status_code != 200:
                logger.error(
                    "sandbox_capture_failed",
                    sandbox_id=sandbox_id,
                    status=response.status_code,
                    detail=response.text,
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text or "Failed to capture session",
                )

            data = response.json()
            stdout = data.get("stdout", "")

            # Parse the storage state JSON
            try:
                storage_state = json.loads(stdout) if stdout.strip() else {"cookies": [], "origins": []}
            except json.JSONDecodeError:
                storage_state = {"cookies": [], "origins": []}

            # Extract domains from cookies
            detected_domains: list[str] = []
            cookies = storage_state.get("cookies", [])
            for cookie in cookies:
                domain = cookie.get("domain", "")
                if domain and domain not in detected_domains:
                    # Remove leading dot from domain
                    clean_domain = domain.lstrip(".")
                    if clean_domain not in detected_domains:
                        detected_domains.append(clean_domain)

            logger.info(
                "sandbox_session_captured",
                sandbox_id=sandbox_id,
                num_cookies=len(cookies),
                num_domains=len(detected_domains),
            )

            return CaptureSessionResponse(
                storage_state=storage_state,
                detected_domains=detected_domains,
            )

    except httpx.RequestError as e:
        logger.error(
            "sandbox_capture_network_error",
            sandbox_id=sandbox_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Sandy service: {e}",
        ) from e


@router.delete("/{sandbox_id}")
async def delete_sandbox(sandbox_id: str) -> dict[str, str]:
    """Terminate and clean up a sandbox.

    Should be called when session capture is complete or cancelled.
    """
    sandy_url, api_key = _get_sandy_config()

    logger.info("sandbox_delete_request", sandbox_id=sandbox_id)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{sandy_url}/api/sandboxes/{sandbox_id}/terminate",
                headers={"Authorization": f"Bearer {api_key}"},
            )

            if response.status_code not in (200, 204, 404):
                logger.warning(
                    "sandbox_delete_failed",
                    sandbox_id=sandbox_id,
                    status=response.status_code,
                )
                # Don't raise - sandbox may already be gone

            logger.info("sandbox_deleted", sandbox_id=sandbox_id)
            return {"status": "deleted", "sandbox_id": sandbox_id}

    except httpx.RequestError as e:
        logger.warning(
            "sandbox_delete_network_error",
            sandbox_id=sandbox_id,
            error=str(e),
        )
        # Don't raise - best effort cleanup
        return {"status": "cleanup_attempted", "sandbox_id": sandbox_id}
