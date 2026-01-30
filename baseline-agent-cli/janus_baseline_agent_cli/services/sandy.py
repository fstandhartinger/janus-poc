"""Sandy sandbox service for complex path execution."""

import asyncio
import base64
import hashlib
import json
import mimetypes
import re
import shlex
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Optional

import httpx
import structlog

from janus_baseline_agent_cli.config import Settings, get_settings
from janus_baseline_agent_cli.logging import log_function_call
from janus_baseline_agent_cli.models import (
    Artifact,
    ArtifactType,
    AssistantMessage,
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ChunkChoice,
    Delta,
    FinishReason,
    GenerationFlags,
    MessageRole,
    Usage,
)
from janus_baseline_agent_cli.models.debug import DebugEventType
from janus_baseline_agent_cli.services.debug import DebugEmitter
from janus_baseline_agent_cli.services.vision import contains_images, get_image_urls
from janus_baseline_agent_cli.services.response_processor import process_agent_response
from janus_baseline_agent_cli.tracing import get_request_id
from janus_baseline_agent_cli.routing import decision_from_metadata, model_for_decision

logger = structlog.get_logger()

CLAUDE_AGENT_DEFAULT_MODEL = "janus-router"
_TOOL_RESULT_PATH_RE = re.compile(r"Full output saved to:\s*(\S+)")
_DATA_IMAGE_URL_RE = re.compile(r"data:(image/[^;]+);base64,([A-Za-z0-9+/=\s]+)")
_LONG_OPERATION_INDICATORS = {
    "git clone": "Cloning repository...",
    "npm install": "Installing dependencies...",
    "pnpm install": "Installing dependencies...",
    "yarn install": "Installing dependencies...",
    "pip install": "Installing Python packages...",
    "apt-get install": "Installing system packages...",
    "apt install": "Installing system packages...",
    "downloading": "Downloading file...",
    "download": "Downloading file...",
    "analyzing": "Analyzing content...",
    "extracting": "Extracting data...",
}

_AGENT_ALIASES = {
    "claude": "claude-code",
    "claude-code": "claude-code",
    "aider": "aider",
    "opencode": "opencode",
    "openhands": "openhands",
    "codex": "codex",
    "roo": "roo-code",
    "roo-code": "roo-code",
    "roo-code-cli": "roo-code",
    "cline": "cline",
    "droid": "droid",
    "builtin": "builtin",
    "run_agent": "builtin",
}

_AGENT_BINARY_NAMES = {
    "claude-code": "claude",
    "roo-code": "roo-code-cli",
    "aider": "aider",
    "opencode": "opencode",
    "codex": "codex",
    "cline": "cline",
    "openhands": "openhands",
    "droid": "droid",
    "builtin": "builtin",
}

_CLI_FALLBACK_AGENTS = {"roo-code", "cline"}


def _parse_sse_events(data: str) -> list[dict[str, Any]]:
    """Parse SSE event data into a list of JSON events."""
    events: list[dict[str, Any]] = []
    current_data = ""

    for line in data.split("\n"):
        if line.startswith("data: "):
            current_data += line[6:]
        elif line == "" and current_data:
            try:
                parsed = json.loads(current_data)
                events.append(parsed)
            except json.JSONDecodeError:
                pass
            current_data = ""

    # Handle any remaining data
    if current_data:
        try:
            parsed = json.loads(current_data)
            events.append(parsed)
        except json.JSONDecodeError:
            pass

    return events


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    text = text.replace("\r", "")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


def _filter_agent_message(text: str) -> Optional[str]:
    """Filter out known noisy agent status lines."""
    trimmed = text.strip()
    if not trimmed:
        return None
    if "Pre-flight check is taking longer than expected" in trimmed:
        return None
    if trimmed.startswith("Running Claude Code with model"):
        return None
    lowered = trimmed.lower()
    if ("claude code" in lowered or "claude-code" in lowered) and "model" in lowered and (
        "starting" in lowered or "running" in lowered
    ):
        return None
    return text


def _long_operation_indicator(text: str | None) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    for needle, indicator in _LONG_OPERATION_INDICATORS.items():
        if needle in lowered:
            return indicator
    return None


def _is_timeout_error(message: str) -> bool:
    lowered = message.lower()
    return "timeout" in lowered or "timed out" in lowered


_REPO_ERROR_MESSAGES = {
    "repository not found": "The repository URL appears to be invalid or private.",
    "fatal: repository": "The repository URL appears to be invalid or private.",
    "not a git repository": "This directory is not a valid git repository.",
    "could not read from remote repository": (
        "Unable to access this repository. It may be private."
    ),
    "permission denied": "Unable to access this repository. It may be private.",
}


def _format_agent_error(message: str) -> str:
    lowered = message.lower()
    for needle, friendly in _REPO_ERROR_MESSAGES.items():
        if needle in lowered:
            return friendly
    if "git" in lowered and _is_timeout_error(lowered):
        return "The repository is taking too long to clone. It may be too large."
    return message


def _build_long_operation_chunk(
    indicator: str | None,
    request_id: str,
    model: str,
    seen: set[str],
) -> Optional[ChatCompletionChunk]:
    if not indicator or indicator in seen:
        return None
    seen.add(indicator)
    return ChatCompletionChunk(
        id=request_id,
        model=model,
        choices=[ChunkChoice(delta=Delta(reasoning_content=f"{indicator}\n"))],
    )


def _extract_tool_result_path(text: str) -> Optional[str]:
    """Extract tool-result file path from Claude Code output."""
    match = _TOOL_RESULT_PATH_RE.search(text or "")
    if not match:
        return None
    return match.group(1).strip()


def _dedupe_result_text(result_text: str, output_parts: list[str]) -> Optional[str]:
    """Avoid duplicating full result text when streaming deltas already emitted."""
    if not result_text:
        return None
    if not output_parts:
        return result_text
    current = "".join(output_parts)
    if not current:
        return result_text
    if result_text == current or result_text in current:
        return None
    if result_text.startswith(current):
        suffix = result_text[len(current):]
        return suffix or None
    return result_text


def _clean_aider_output(text: str) -> str:
    """Clean up Aider-specific output formatting.

    Removes:
    - "Added X to the chat." messages
    - "► **THINKING**" / "► **ANSWER**" markers
    - "Applied edit to X" messages
    - Sandy web dev context noise
    """
    lines = text.split("\n")
    cleaned_lines = []
    skip_until_answer = False

    for line in lines:
        stripped = line.strip()

        # Skip common Aider noise
        if stripped.startswith("Added ") and " to the chat" in stripped:
            continue
        if stripped.startswith("Applied edit to "):
            continue
        if stripped == "► **THINKING**":
            skip_until_answer = True
            continue
        if stripped == "► **ANSWER**":
            skip_until_answer = False
            continue

        # Skip thinking content between markers
        if skip_until_answer:
            continue

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines).strip()

    # Remove excessive blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result


def _trim_bootstrap_output(text: str, max_lines: int = 40, max_chars: int = 4000) -> str:
    """Trim verbose bootstrap logs to keep streaming lightweight."""
    if not text:
        return text
    lines = text.splitlines()
    if len(lines) <= max_lines and len(text) <= max_chars:
        return text
    head = lines[:15]
    tail = lines[-15:] if len(lines) > 20 else []
    trimmed = "\n".join(
        head + (["... (bootstrap output trimmed) ..."] if tail else []) + tail
    )
    if len(trimmed) > max_chars:
        trimmed = trimmed[:max_chars] + "\n... (trimmed)"
    return trimmed


def _debug_step_for_tool(tool_name: str) -> str:
    normalized = tool_name.lower()
    if "search" in normalized:
        return "TOOL_SEARCH"
    if "image" in normalized or "vision" in normalized:
        return "TOOL_IMG"
    if "file" in normalized or "read" in normalized or "write" in normalized:
        return "TOOL_FILES"
    if "code" in normalized or "exec" in normalized or "python" in normalized:
        return "TOOL_CODE"
    return "TOOL_CODE"


@dataclass
class ExecResult:
    """Result for sandbox command execution."""

    stdout: str
    stderr: str
    exit_code: int


class SandyService:
    """Service for executing tasks in Sandy sandboxes."""

    _max_inline_bytes = 1_000_000
    _max_inline_image_bytes = 5_000_000
    # Include common pip --user install paths and standard paths
    # Note: Using actual paths instead of unexpanded shell variables
    _default_path = (
        "/workspace/agent-pack/bin:"  # agent pack binaries inside sandbox workdir
        "/root/.local/bin:"  # pip --user for root
        "/usr/local/bin:"  # system-wide pip installs
        "/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
    )

    def __init__(
        self,
        settings: Settings,
        client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    ) -> None:
        self._settings = settings
        self._base_url = settings.sandy_base_url
        self._api_key = settings.sandy_api_key
        self._timeout = settings.sandy_agent_timeout
        self._client_factory = client_factory or httpx.AsyncClient
        self._baseline_root = Path(__file__).resolve().parents[2]
        self._agent_pack_path = self._resolve_path(settings.agent_pack_path)
        self._system_prompt_path = self._resolve_path(settings.system_prompt_path)
        self._artifact_port = settings.artifact_port
        self._artifact_dir = settings.artifact_dir
        self._artifact_ttl = settings.artifact_ttl_seconds
        self._artifact_grace_seconds = settings.artifact_grace_seconds
        self._screenshot_dir = f"{self._artifact_dir.rstrip('/')}/screenshots"
        self._baseline_agent = settings.baseline_agent.strip() if settings.baseline_agent else "aider"

    @property
    def is_available(self) -> bool:
        """Check if Sandy is configured."""
        return bool(self._base_url)

    @log_function_call
    async def create_sandbox(self) -> str:
        """Create a new sandbox and return its ID."""
        async with self._client_factory() as client:
            result = await self._create_sandbox(client)
        if not result:
            raise RuntimeError("Failed to create sandbox")
        sandbox_id, _ = result
        return sandbox_id

    @log_function_call
    async def exec(self, sandbox_id: str, command: str) -> ExecResult:
        """Execute a command in a sandbox."""
        async with self._client_factory() as client:
            stdout, stderr, exit_code = await self._exec_in_sandbox(
                client, sandbox_id, command
            )
        return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)

    @log_function_call
    async def write_file(self, sandbox_id: str, path: str, content: str | bytes) -> bool:
        """Write a file into the sandbox."""
        data = content.encode("utf-8") if isinstance(content, str) else content
        async with self._client_factory() as client:
            if await self._write_file(client, sandbox_id, path, data):
                return True
            return await self._write_file_via_exec(client, sandbox_id, path, data)

    @log_function_call
    async def read_file(self, sandbox_id: str, path: str) -> str:
        """Read a file from the sandbox."""
        async with self._client_factory() as client:
            data = await self._read_file(client, sandbox_id, path)
        if data is None:
            raise FileNotFoundError(path)
        return data.decode("utf-8", errors="replace")

    @log_function_call
    async def terminate(self, sandbox_id: str) -> None:
        """Terminate a sandbox."""
        async with self._client_factory() as client:
            await self._terminate_sandbox(client, sandbox_id)

    @log_function_call
    async def check_sandbox(self, sandbox_id: str) -> bool:
        """Check whether a sandbox is responsive."""
        async with self._client_factory() as client:
            _, _, exit_code = await self._exec_in_sandbox(client, sandbox_id, "true")
        return exit_code == 0

    @log_function_call
    async def reset_sandbox(self, sandbox_id: str) -> None:
        """Reset sandbox state for reuse."""
        artifact_dir = shlex.quote(self._artifact_dir.rstrip("/"))
        command = f"rm -rf -- {artifact_dir} && mkdir -p {artifact_dir}"
        async with self._client_factory() as client:
            await self._exec_in_sandbox(client, sandbox_id, command)

    @log_function_call
    async def prepare_warm_sandbox(
        self,
        request: ChatCompletionRequest | None = None,
        has_images: bool = False,
    ) -> Optional[tuple[str, str | None]]:
        """Create and warm a sandbox with the agent pack bootstrapped."""
        if not self.is_available:
            return None
        async with self._client_factory() as client:
            sandbox_info = await self._create_sandbox(client)
            if not sandbox_info:
                return None
            sandbox_id, public_url = sandbox_info
            try:
                if not await self._upload_agent_pack(client, sandbox_id):
                    await self._terminate_sandbox(client, sandbox_id)
                    return None
                bootstrap_stdout, bootstrap_stderr, bootstrap_exit = await self._run_bootstrap(
                    client, sandbox_id, public_url, request, has_images
                )
                if bootstrap_exit != 0:
                    logger.warning(
                        "sandy_bootstrap_failed",
                        sandbox_id=sandbox_id,
                        error=bootstrap_stderr or "bootstrap failed",
                    )
                    await self._terminate_sandbox(client, sandbox_id)
                    return None
                if bootstrap_stdout:
                    logger.info(
                        "sandy_bootstrap_output",
                        sandbox_id=sandbox_id,
                        stdout=bootstrap_stdout,
                    )

                # Inject browser session if specified
                if request and request.browser_session_id:
                    auth_token = self._resolve_auth_token(request)
                    session_data = await self._fetch_browser_session(
                        client, request.browser_session_id, auth_token
                    )
                    if session_data:
                        await self._inject_browser_session(
                            client,
                            sandbox_id,
                            session_data["storage_state"],
                            session_data.get("domains"),
                        )
                    else:
                        logger.warning(
                            "browser_session_fetch_failed",
                            sandbox_id=sandbox_id,
                            session_id=request.browser_session_id,
                        )

                return sandbox_id, public_url
            except Exception as exc:
                logger.warning(
                    "sandy_warm_sandbox_error",
                    sandbox_id=sandbox_id,
                    error=str(exc),
                )
                await self._terminate_sandbox(client, sandbox_id)
                return None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request_id = get_request_id()
        if request_id:
            headers["X-Request-Id"] = request_id
        return headers

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the baseline root if needed."""
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return (self._baseline_root / candidate).resolve()

    def _agent_pack_dest_root(self) -> str:
        """Get the agent pack destination path inside the sandbox."""
        return "/workspace/agent-pack"

    def _iter_agent_pack_files(self) -> list[Path]:
        """Collect agent pack files to upload."""
        if not self._agent_pack_path.exists():
            return []
        return [path for path in self._agent_pack_path.rglob("*") if path.is_file()]

    def _artifact_url_base(self, sandbox_id: str, public_url: str | None) -> str:
        """Resolve the base URL for sandbox artifacts."""
        if public_url:
            return f"{public_url.rstrip('/')}/artifacts"
        if self._base_url:
            return f"{self._base_url.rstrip('/')}/sandbox/{sandbox_id}/artifacts"
        return "/artifacts"

    def _sandbox_url(self, sandbox_id: str, public_url: str | None) -> str:
        """Resolve the base URL for sandbox access."""
        if public_url:
            return public_url.rstrip("/")
        if self._base_url:
            return f"{self._base_url.rstrip('/')}/sandbox/{sandbox_id}"
        return ""

    def _build_agent_env(
        self,
        sandbox_id: str,
        public_url: str | None,
        request: ChatCompletionRequest | None = None,
        has_images: bool = False,
    ) -> dict[str, str]:
        """Build environment variables for the CLI agent."""
        sandbox_url = self._sandbox_url(sandbox_id, public_url)
        artifact_base = self._artifact_url_base(sandbox_id, public_url)
        chutes_api_key = (
            (request.chutes_access_token if request else None)
            or self._settings.chutes_api_key
            or self._settings.openai_api_key
            or ""
        )
        chutes_api_url = self._settings.chutes_api_base_effective
        auth_token = self._resolve_auth_token(request)
        env = {
            "JANUS_WORKSPACE": "/workspace",
            "JANUS_AGENT_PACK": self._agent_pack_dest_root(),
            "JANUS_DOCS_ROOT": "/workspace/docs/models",
            "JANUS_SYSTEM_PROMPT_PATH": f"{self._agent_pack_dest_root()}/prompts/system.md",
            "JANUS_ENABLE_WEB_SEARCH": str(self._settings.enable_web_search).lower(),
            "JANUS_ENABLE_CODE_EXECUTION": str(self._settings.enable_code_execution).lower(),
            "JANUS_ENABLE_FILE_TOOLS": str(self._settings.enable_file_tools).lower(),
            "JANUS_ENABLE_NETWORK": "true",
            "CHUTES_API_KEY": chutes_api_key,
            "CHUTES_API_URL": chutes_api_url,
            "CHUTES_API_BASE": chutes_api_url,
            "CHUTES_SEARCH_URL": self._settings.chutes_search_url,
            "SERPER_API_KEY": self._settings.serper_api_key or "",
            "SEARXNG_API_URL": self._settings.searxng_api_url or "",
            "JANUS_SANDBOX_ID": sandbox_id,
            "JANUS_SANDBOX_URL": sandbox_url,
            "JANUS_SANDBOX_PUBLIC_URL": public_url or "",
            "JANUS_ARTIFACT_URL_BASE": artifact_base,
            "JANUS_ARTIFACT_BASE_URL": artifact_base,
            "JANUS_ARTIFACTS_DIR": self._artifact_dir,
            "JANUS_ARTIFACT_PORT": str(self._artifact_port),
            "JANUS_SCREENSHOT_DIR": self._screenshot_dir,
            "JANUS_VISION_MODEL": self._settings.vision_model_primary,
            "JANUS_VISION_FALLBACK": self._settings.vision_model_fallback,
            "JANUS_HAS_IMAGES": str(has_images).lower(),
            "SANDY_API_KEY": auth_token or "",
            "SANDY_BASE_URL": self._settings.sandy_base_url or "",
            "JANUS_MAX_CHILD_SANDBOXES": "5",
            "JANUS_DEFAULT_SANDBOX_TTL": "600",
            "JANUS_GIT_TIMEOUT": str(self._settings.sandy_git_timeout),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_HTTP_LOW_SPEED_TIME": str(self._settings.sandy_git_timeout),
            "GIT_HTTP_LOW_SPEED_LIMIT": "1",
            "PATH": self._default_path,
        }
        router_url = self._settings.public_router_url
        if not router_url and self._settings.use_model_router:
            router_url = f"http://{self._settings.router_host}:{self._settings.router_port}"
        if router_url:
            anthropic_base = router_url.rstrip("/")
            if anthropic_base.endswith("/v1"):
                anthropic_base = anthropic_base[:-3]
            env.setdefault("ANTHROPIC_BASE_URL", anthropic_base)
            if chutes_api_key:
                env.setdefault("ANTHROPIC_API_KEY", chutes_api_key)
                env.setdefault("ANTHROPIC_AUTH_TOKEN", chutes_api_key)
        if chutes_api_key:
            env.setdefault("OPENAI_API_KEY", chutes_api_key)
        if chutes_api_url:
            env.setdefault("OPENAI_BASE_URL", chutes_api_url)
            env.setdefault("OPENAI_API_BASE", chutes_api_url)
            env.setdefault("CHUTES_BASE_URL", chutes_api_url)
        if self._memory_tool_enabled(request):
            env.update(
                {
                    "JANUS_ENABLE_MEMORY_TOOL": "true",
                    "JANUS_MEMORY_SERVICE_URL": self._settings.memory_service_url,
                    "JANUS_MEMORY_USER_ID": request.user_id or "",
                }
            )
        else:
            env["JANUS_ENABLE_MEMORY_TOOL"] = "false"

        # Browser session injection
        if request and request.browser_session_id:
            env["JANUS_BROWSER_SESSION_ID"] = request.browser_session_id
            env["JANUS_BROWSER_PROFILE_PATH"] = "/workspace/.browser-profile"

        return env

    def _normalize_agent_name(self, agent: str | None) -> str:
        if not agent:
            return ""
        normalized = agent.strip().lower()
        return _AGENT_ALIASES.get(normalized, normalized)

    def _agent_binary_name(self, agent: str) -> str:
        return _AGENT_BINARY_NAMES.get(agent, agent)

    def requires_cli_execution(self, requested_agent: str | None) -> bool:
        normalized = self._normalize_agent_name(requested_agent or self._baseline_agent)
        return normalized in _CLI_FALLBACK_AGENTS

    def _router_api_base(self, router_url: str, agent: str) -> str:
        base = router_url.rstrip("/")
        if agent in {"claude", "claude-code"}:
            return base[:-3] if base.endswith("/v1") else base
        return base if base.endswith("/v1") else f"{base}/v1"

    def _resolve_auth_token(self, request: ChatCompletionRequest | None) -> str | None:
        if request is None:
            return self._settings.sandy_api_key
        auth_token = getattr(request, "_auth_token", None)
        return auth_token or self._settings.sandy_api_key

    def _memory_tool_enabled(self, request: ChatCompletionRequest | None) -> bool:
        if request is None:
            return False
        if not self._settings.enable_memory_feature:
            return False
        if not request.enable_memory or not request.user_id:
            return False
        for message in request.messages:
            if self._content_has_memory_reference(message.content):
                return True
        return False

    def _content_has_memory_reference(self, content: object) -> bool:
        if isinstance(content, str):
            return "<memory-references>" in content
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text" and "<memory-references>" in str(
                        part.get("text", "")
                    ):
                        return True
                else:
                    text = getattr(part, "text", None)
                    if text and "<memory-references>" in text:
                        return True
        return False

    async def _fetch_browser_session(
        self,
        client: httpx.AsyncClient,
        session_id: str,
        auth_token: str | None,
    ) -> dict[str, Any] | None:
        """Fetch browser session state from the session service.

        Args:
            client: HTTP client
            session_id: Session ID to fetch
            auth_token: Auth token for the session service

        Returns:
            Session data with storage_state and domains, or None if fetch fails
        """
        service_url = self._settings.browser_session_service_url
        if not service_url:
            logger.warning("browser_session_service_url not configured")
            return None

        try:
            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            # Fetch session state
            response = await client.get(
                f"{service_url}/sessions/{session_id}/state",
                headers=headers,
                timeout=10.0,
            )

            if response.status_code == 404:
                logger.warning("browser_session_not_found", session_id=session_id)
                return None

            if response.status_code == 410:
                logger.warning("browser_session_expired", session_id=session_id)
                return None

            response.raise_for_status()
            state_data = response.json()

            # Also fetch session metadata for domains
            meta_response = await client.get(
                f"{service_url}/sessions/{session_id}",
                headers=headers,
                timeout=10.0,
            )
            domains = []
            if meta_response.status_code == 200:
                meta_data = meta_response.json()
                domains = meta_data.get("domains", [])

            return {
                "storage_state": state_data.get("storage_state", {}),
                "domains": domains,
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                "browser_session_fetch_error",
                session_id=session_id,
                status_code=e.response.status_code,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "browser_session_fetch_error",
                session_id=session_id,
                error=str(e),
            )
            return None

    async def _inject_browser_session(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        storage_state: dict[str, Any],
        domains: list[str] | None = None,
    ) -> bool:
        """Inject browser session into sandbox.

        Creates a Chrome-compatible browser profile from the storage state
        and writes it to the sandbox.

        Args:
            client: HTTP client
            sandbox_id: Sandbox ID to inject into
            storage_state: Playwright-compatible storage state
            domains: List of domains the session is valid for

        Returns:
            True if injection succeeded, False otherwise
        """
        try:
            # Import the profile conversion utility
            import sys
            import tempfile
            import os

            # Add agent-pack to path for imports
            agent_pack_lib = Path(__file__).resolve().parents[2] / "agent-pack" / "lib"
            if str(agent_pack_lib) not in sys.path:
                sys.path.insert(0, str(agent_pack_lib))

            from session_profile import create_browser_profile, extract_domains_from_storage_state

            # Auto-detect domains if not provided
            if not domains:
                domains = extract_domains_from_storage_state(storage_state)

            # Create profile in a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                profile_path = os.path.join(temp_dir, "profile")
                create_browser_profile(storage_state, profile_path, domains)

                # Upload each file to the sandbox
                sandbox_profile_path = "/workspace/.browser-profile"
                for root, dirs, files in os.walk(profile_path):
                    for file in files:
                        local_path = os.path.join(root, file)
                        rel_path = os.path.relpath(local_path, profile_path)
                        sandbox_file_path = f"{sandbox_profile_path}/{rel_path}"

                        with open(local_path, "rb") as f:
                            content = f.read()

                        # Write file to sandbox
                        if not await self._write_file(client, sandbox_id, sandbox_file_path, content):
                            # Try alternative method
                            if not await self._write_file_via_exec(client, sandbox_id, sandbox_file_path, content):
                                logger.warning(
                                    "browser_profile_file_write_failed",
                                    sandbox_id=sandbox_id,
                                    file=sandbox_file_path,
                                )

            logger.info(
                "browser_session_injected",
                sandbox_id=sandbox_id,
                domains=domains,
            )
            return True

        except Exception as e:
            logger.error(
                "browser_session_injection_error",
                sandbox_id=sandbox_id,
                error=str(e),
            )
            return False

    def _build_agent_command(
        self,
        agent: str,
        task: str,
        sandbox_id: str,
        public_url: str | None,
        request: ChatCompletionRequest | None = None,
        has_images: bool = False,
    ) -> str:
        """Build the CLI agent command."""
        env_dict = self._build_agent_env(sandbox_id, public_url, request, has_images)
        env_parts = [
            f"{key}={shlex.quote(str(value))}"
            for key, value in env_dict.items()
        ]
        quoted_task = shlex.quote(task)
        agent_pack_root = self._agent_pack_dest_root()
        system_prompt_path = f"{agent_pack_root}/prompts/system.md"

        # Log the full task being sent to the agent
        logger.info(
            "agent_task_prompt",
            agent=agent,
            task_length=len(task),
            task_preview=task[:500] if len(task) > 500 else task,
            system_prompt_path=system_prompt_path,
        )

        if agent == "builtin":
            command = [
                "python",
                f"{agent_pack_root}/run_agent.py",
                quoted_task,
            ]
        elif agent in {"claude", "claude-code"}:
            # Claude Code CLI agent (print mode)
            command = [
                "claude",
                "-p",
                "--verbose",
                "--output-format",
                "text",
                "--no-session-persistence",
                "--permission-mode",
                "acceptEdits",
                "--add-dir",
                "/workspace",
                "--allowedTools",
                "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch",
            ]
            command += ["--append-system-prompt-file", system_prompt_path]
            command += ["--", quoted_task]
        elif agent == "aider":
            # Aider needs specific flags for non-interactive mode
            # --yes-always: auto-confirm all changes
            # --no-git: don't require git repo
            # --message: the task to execute
            # --read: include system prompt as context
            command = [
                "aider",
                "--yes-always",
                "--no-git",
                "--read", system_prompt_path,
                "--message", quoted_task,
            ]
        elif agent == "opencode":
            # OpenCode CLI agent
            command = [
                "opencode",
                "run",
                quoted_task,
                "--format",
                "json",
                "--context",
                system_prompt_path,
            ]
        elif agent == "codex":
            # Codex CLI agent
            command = [
                "codex",
                "--output-format",
                "json",
                quoted_task,
            ]
        elif agent == "roo-code":
            # Roo Code CLI agent
            command = [
                "roo-code-cli",
                "--auto-approve",
                quoted_task,
            ]
        elif agent == "cline":
            # Cline CLI agent
            command = [
                "cline",
                quoted_task,
                "--auto-approve",
            ]
        elif agent == "openhands":
            # OpenHands CLI
            command = [
                "openhands",
                "--non-interactive",
                "--instructions", system_prompt_path,
                quoted_task,
            ]
        else:
            # Generic fallback - just pass the task
            command = [agent, quoted_task]

        full_command = " ".join(["env", *env_parts, *command])
        if agent in {"claude", "claude-code"}:
            full_command = f"cd /workspace && {full_command}"
        logger.info(
            "agent_command_built",
            agent=agent,
            command_preview=full_command[:1000],
            full_command_length=len(full_command),
        )
        return full_command

    def _agent_candidates(self, requested_agent: str | None = None) -> list[str]:
        """Determine preferred agent order.

        Supported agents:
        - claude-code: Anthropic's Claude Code CLI
        - roo-code: Roo Code CLI agent
        - cline: Cline CLI agent
        - opencode: Factory OpenCode agent
        - codex: OpenAI Codex CLI
        - aider: AI pair programmer
        - openhands: OpenHands CLI
        - builtin: Simple template-based fallback
        """
        requested = self._normalize_agent_name(
            requested_agent or self._baseline_agent
        )
        logger.info(
            "agent_candidates_config",
            requested_agent=requested,
            baseline_agent_setting=self._baseline_agent,
        )
        if requested in {"builtin", "run_agent"}:
            return ["builtin"]
        if requested in {"claude", "claude-code"}:
            return [
                "claude-code",
                "roo-code",
                "cline",
                "opencode",
                "codex",
                "aider",
                "openhands",
                "builtin",
            ]
        if requested:
            return [
                requested,
                "claude-code",
                "roo-code",
                "cline",
                "opencode",
                "codex",
                "aider",
                "openhands",
                "builtin",
            ]
        # Default order: prefer Claude Code, then Roo/Cline, then other agents
        return [
            "claude-code",
            "roo-code",
            "cline",
            "opencode",
            "codex",
            "aider",
            "openhands",
            "builtin",
        ]

    async def _select_agent(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        requested_agent: str | None = None,
    ) -> str:
        """Pick an available CLI agent inside the sandbox."""
        candidates = self._agent_candidates(requested_agent)
        logger.info(
            "agent_selection_start",
            candidates=candidates,
            baseline_agent_config=self._baseline_agent,
            path=self._default_path,
        )

        # First, log what's available in the PATH for debugging
        path_check_cmd = (
            "PATH="
            f"{shlex.quote(self._default_path)} "
            "ls -la /root/.local/bin/ 2>/dev/null || echo 'No /root/.local/bin'; "
            "which aider claude opencode openhands codex roo-code-cli cline 2>/dev/null "
            "|| echo 'None found in PATH'"
        )
        path_stdout, path_stderr, _ = await self._exec_in_sandbox(
            client, sandbox_id, path_check_cmd
        )
        logger.info(
            "agent_path_debug",
            path_contents=path_stdout[:500] if path_stdout else "",
            path_errors=path_stderr[:200] if path_stderr else "",
        )

        for candidate in candidates:
            if candidate == "builtin":
                logger.info("agent_selected", agent="builtin", reason="fallback_reached")
                return "builtin"

            binary_name = self._agent_binary_name(
                self._normalize_agent_name(candidate)
            )

            check_cmd = f"PATH={shlex.quote(self._default_path)} command -v {shlex.quote(binary_name)}"
            stdout, stderr, exit_code = await self._exec_in_sandbox(
                client,
                sandbox_id,
                check_cmd,
            )
            logger.info(
                "agent_check",
                candidate=candidate,
                binary_name=binary_name,
                exit_code=exit_code,
                found_path=stdout.strip() if stdout else "",
                stderr=stderr.strip()[:200] if stderr else "",
            )
            if exit_code == 0 and stdout.strip():
                logger.info(
                    "agent_selected",
                    agent=candidate,
                    binary_name=binary_name,
                    path=stdout.strip(),
                    reason="found_in_path",
                )
                return candidate

        logger.warning("agent_selected", agent="builtin", reason="no_candidates_found_in_path")
        return "builtin"

    async def _write_file(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        dest_path: str,
        content: bytes,
    ) -> bool:
        """Write a file into the sandbox via Sandy file API."""
        try:
            try:
                decoded = content.decode("utf-8")
            except UnicodeDecodeError:
                return False
            payload = {"path": dest_path, "content": decoded}
            response = await client.post(
                f"{self._base_url}/api/sandboxes/{sandbox_id}/files/write",
                json=payload,
                headers=self._get_headers(),
                timeout=self._timeout,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning("sandy_files_write_error", error=str(e), path=dest_path)
            return False

    async def _write_file_via_exec(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        dest_path: str,
        content: bytes,
    ) -> bool:
        """Fallback file write using exec."""
        encoded = base64.b64encode(content).decode("utf-8")
        dest_dir = str(Path(dest_path).parent)
        command = (
            f"mkdir -p {shlex.quote(dest_dir)} && "
            f"printf %s {shlex.quote(encoded)} | base64 -d > {shlex.quote(dest_path)}"
        )
        stdout, stderr, exit_code = await self._exec_in_sandbox(
            client, sandbox_id, command
        )
        if exit_code != 0:
            logger.warning(
                "sandy_write_fallback_error",
                path=dest_path,
                stdout=stdout,
                stderr=stderr,
            )
        return exit_code == 0

    async def _read_file(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        path: str,
    ) -> Optional[bytes]:
        """Read a file from the sandbox."""
        try:
            response = await client.get(
                f"{self._base_url}/api/sandboxes/{sandbox_id}/files/read",
                params={"path": path},
                headers=self._get_headers(),
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.warning("sandy_files_read_error", error=str(e), path=path)
            return None

    async def _list_artifact_paths(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
    ) -> list[str]:
        """List artifact files in the sandbox."""
        command = f"find {shlex.quote(self._artifact_dir)} -maxdepth 1 -type f"
        stdout, _, exit_code = await self._exec_in_sandbox(client, sandbox_id, command)
        if exit_code != 0 or not stdout:
            return []
        return [line.strip() for line in stdout.splitlines() if line.strip()]

    async def _list_screenshot_metadata_paths(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
    ) -> list[str]:
        """List screenshot metadata files in the sandbox."""
        command = (
            f"find {shlex.quote(self._screenshot_dir)} -maxdepth 1 "
            "-type f -name '*.json' 2>/dev/null"
        )
        stdout, _, exit_code = await self._exec_in_sandbox(client, sandbox_id, command)
        if exit_code != 0 or not stdout:
            return []
        return [line.strip() for line in stdout.splitlines() if line.strip()]

    async def _load_screenshot_payload(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        metadata_path: str,
    ) -> Optional[dict[str, object]]:
        """Load screenshot metadata and image data into a payload."""
        metadata_bytes = await self._read_file(client, sandbox_id, metadata_path)
        if not metadata_bytes:
            return None
        try:
            metadata = json.loads(metadata_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            return None
        if not isinstance(metadata, dict):
            return None

        image_path = f"{self._screenshot_dir.rstrip('/')}/{Path(metadata_path).stem}.png"
        image_bytes = await self._read_file(client, sandbox_id, image_path)
        if not image_bytes:
            return None

        return {
            "url": str(metadata.get("url", "")),
            "title": str(metadata.get("title", "")),
            "timestamp": float(metadata.get("timestamp", 0.0)),
            "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
        }

    async def _collect_screenshot_events(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        seen: set[str],
        request_id: str,
        model: str,
    ) -> list[ChatCompletionChunk]:
        """Collect new screenshot events from the sandbox."""
        metadata_paths = await self._list_screenshot_metadata_paths(client, sandbox_id)
        if not metadata_paths:
            return []

        events: list[ChatCompletionChunk] = []
        for path in sorted(metadata_paths):
            if path in seen:
                continue
            payload = await self._load_screenshot_payload(client, sandbox_id, path)
            if not payload:
                continue
            seen.add(path)
            events.append(
                ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(janus={"event": "screenshot", "payload": payload})
                        )
                    ],
                )
            )
        return events

    def _artifact_type_for(self, mime_type: str) -> ArtifactType:
        """Map MIME type to artifact type."""
        if mime_type.startswith("image/"):
            return ArtifactType.IMAGE
        return ArtifactType.FILE

    def _build_data_url(self, data: bytes, mime_type: str) -> str:
        """Build base64 data URL for artifact payloads."""
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _safe_tool_result_path(self, path: str) -> bool:
        if not path or not path.startswith("/"):
            return False
        if ".." in path:
            return False
        return path.startswith("/root/.claude/projects/") or path.startswith("/workspace/")

    async def _read_tool_result_text(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        path: str,
        max_chars: int = 200_000,
    ) -> Optional[str]:
        """Read a tool-result file if it exists and looks safe."""
        if not self._safe_tool_result_path(path):
            return None
        data = await self._read_file(client, sandbox_id, path)
        if not data:
            return None
        text = data.decode("utf-8", errors="ignore")
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... (tool output truncated)"
        return text

    async def _materialize_data_url_images(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        text: str,
    ) -> str:
        """Convert data URL images in text into /workspace/artifacts files."""
        if not text or "data:image" not in text:
            return text

        updated = text
        for match in list(_DATA_IMAGE_URL_RE.finditer(text)):
            mime_type = match.group(1)
            encoded = match.group(2) or ""
            encoded = re.sub(r"\s+", "", encoded)
            if not encoded:
                continue
            try:
                data = base64.b64decode(encoded, validate=False)
            except Exception:
                continue
            if not data:
                continue
            sha256 = hashlib.sha256(data).hexdigest()
            ext = mimetypes.guess_extension(mime_type) or ".png"
            filename = f"tool-result-{sha256[:12]}{ext}"
            dest_path = f"{self._artifact_dir.rstrip('/')}/{filename}"
            if not await self._write_file(client, sandbox_id, dest_path, data):
                await self._write_file_via_exec(client, sandbox_id, dest_path, data)
            updated = updated.replace(match.group(0), f"/artifacts/{filename}")
        return updated

    async def _collect_artifacts(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        public_url: str | None,
    ) -> list[Artifact]:
        """Collect artifact descriptors from the sandbox."""
        artifact_paths = await self._list_artifact_paths(client, sandbox_id)
        if not artifact_paths:
            return []

        artifacts: list[Artifact] = []
        artifact_base = self._artifact_url_base(sandbox_id, public_url)

        for path in artifact_paths:
            data = await self._read_file(client, sandbox_id, path)
            if data is None:
                continue
            mime_type, _ = mimetypes.guess_type(path)
            mime_type = mime_type or "application/octet-stream"
            size_bytes = len(data)
            sha256 = hashlib.sha256(data).hexdigest()
            if mime_type.startswith("image/"):
                filename = Path(path).name
                url = f"{artifact_base.rstrip('/')}/{filename}"
            else:
                if size_bytes <= self._max_inline_bytes:
                    url = self._build_data_url(data, mime_type)
                else:
                    filename = Path(path).name
                    url = f"{artifact_base.rstrip('/')}/{filename}"

            artifacts.append(
                Artifact(
                    id=f"artf_{uuid.uuid4().hex[:12]}",
                    type=self._artifact_type_for(mime_type),
                    mime_type=mime_type,
                    display_name=Path(path).name,
                    size_bytes=size_bytes,
                    sha256=sha256,
                    ttl_seconds=self._artifact_ttl,
                    url=url,
                )
            )

        return artifacts

    def _format_artifact_links(self, artifacts: list[Artifact]) -> str:
        """Render artifact markdown links for responses."""
        return "\n".join(
            f"- [{artifact.display_name}]({artifact.url})" for artifact in artifacts
        )

    async def _upload_agent_pack(
        self, client: httpx.AsyncClient, sandbox_id: str
    ) -> bool:
        """Upload the agent pack into the sandbox."""
        files = self._iter_agent_pack_files()
        if not files:
            logger.error("agent_pack_missing", path=str(self._agent_pack_path))
            return False

        dest_root = self._agent_pack_dest_root()
        created_dirs: set[str] = set()

        for file_path in files:
            rel_path = file_path.relative_to(self._agent_pack_path).as_posix()
            dest_path = f"{dest_root}/{rel_path}"
            dest_dir = str(Path(dest_path).parent)
            if dest_dir not in created_dirs:
                await self._exec_in_sandbox(
                    client, sandbox_id, f"mkdir -p {shlex.quote(dest_dir)}"
                )
                created_dirs.add(dest_dir)

            content = file_path.read_bytes()
            if not await self._write_file(client, sandbox_id, dest_path, content):
                if not await self._write_file_via_exec(
                    client, sandbox_id, dest_path, content
                ):
                    return False

        return True

    async def _run_bootstrap(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        public_url: str | None,
        request: ChatCompletionRequest | None = None,
        has_images: bool = False,
    ) -> tuple[str, str, int]:
        """Run the agent pack bootstrap script inside the sandbox."""
        env_parts = [
            f"{key}={shlex.quote(str(value))}"
            for key, value in self._build_agent_env(
                sandbox_id, public_url, request, has_images
            ).items()
        ]
        command = " ".join(
            [
                "env",
                *env_parts,
                "bash",
                f"{self._agent_pack_dest_root()}/bootstrap.sh",
            ]
        )
        return await self._exec_in_sandbox(client, sandbox_id, command)

    async def _create_sandbox(
        self, client: httpx.AsyncClient
    ) -> Optional[tuple[str, str | None]]:
        """Create a new Sandy sandbox."""
        try:
            payload: dict[str, object] = {
                "priority": 1,  # Integer priority (1=normal)
                "ttl_seconds": self._timeout,
            }
            if self._artifact_port:
                payload["expose_ports"] = [self._artifact_port]
            response = await client.post(
                f"{self._base_url}/api/sandboxes",
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            # Sandy returns sandboxId, not sandbox_id
            sandbox_id = data.get("sandboxId") or data.get("sandbox_id") or data.get("id")
            if sandbox_id is None:
                return None
            # Sandy returns url, not public_url
            public_url = data.get("url") or data.get("public_url") or data.get("sandbox_url")
            return str(sandbox_id), str(public_url) if public_url else None
        except Exception as e:
            logger.error("sandy_create_error", error=str(e))
            return None

    async def _exec_in_sandbox(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        command: str,
    ) -> tuple[str, str, int]:
        """Execute a command in a sandbox."""
        try:
            response = await client.post(
                f"{self._base_url}/api/sandboxes/{sandbox_id}/exec",
                json={"command": command, "timeout": self._timeout},
                headers=self._get_headers(),
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            return (
                data.get("stdout", ""),
                data.get("stderr", ""),
                data.get("exit_code", 0),
            )
        except Exception as e:
            logger.error("sandy_exec_error", error=str(e))
            return "", str(e), 1

    async def _terminate_sandbox(
        self, client: httpx.AsyncClient, sandbox_id: str
    ) -> None:
        """Terminate a sandbox."""
        try:
            await client.post(
                f"{self._base_url}/api/sandboxes/{sandbox_id}/terminate",
                headers=self._get_headers(),
            )
        except Exception as e:
            logger.warning("sandy_terminate_error", error=str(e))

    async def _terminate_sandbox_after_delay(
        self, sandbox_id: str, delay_seconds: float
    ) -> None:
        """Terminate a sandbox after a delay using a fresh client."""
        try:
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            async with self._client_factory() as client:
                await self._terminate_sandbox(client, sandbox_id)
        except Exception as e:
            logger.warning("sandy_terminate_delayed_error", error=str(e))

    def _schedule_sandbox_termination(self, sandbox_id: str, delay_seconds: float) -> None:
        """Schedule sandbox termination without blocking the response."""
        if delay_seconds <= 0:
            return
        asyncio.create_task(
            self._terminate_sandbox_after_delay(sandbox_id, delay_seconds)
        )

    async def _run_agent_via_api(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        agent: str,
        model: str,
        prompt: str,
        request: ChatCompletionRequest | None = None,
        public_url: str | None = None,
        has_images: bool = False,
        max_duration: int = 600,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Run an agent via Sandy's built-in agent/run API.

        This uses Sandy's agent runner which handles:
        - Agent configuration with yolo mode (--permission-mode acceptEdits, etc.)
        - Environment setup with API keys
        - Config file creation for each agent
        - SSE streaming output

        Events yielded:
        - status: Progress messages
        - agent-output: Raw agent output (especially for claude-code)
        - files-update: File change notifications
        - heartbeat: Keep-alive
        - output: Text output
        - complete: Final completion event
        - error: Error events
        """
        url = f"{self._base_url}/api/sandboxes/{sandbox_id}/agent/run"
        payload: dict[str, Any] = {
            "agent": agent,
            "model": model,
            "prompt": prompt,
            "maxDuration": max_duration,
            "rawPrompt": True,  # Skip web dev context wrapping (camelCase for Sandy API)
        }
        env = self._build_agent_env(sandbox_id, public_url, request, has_images)
        if env:
            payload["env"] = env
            payload["envVars"] = env
            system_prompt_path = env.get("JANUS_SYSTEM_PROMPT_PATH")
            if system_prompt_path:
                payload["systemPromptPath"] = system_prompt_path

        # Pass the public router URL if configured - enables smart model switching,
        # 429 fallbacks, and multimodal routing for Sandy agents
        router_url = self._settings.public_router_url
        if not router_url and self._settings.use_model_router:
            router_url = f"http://{self._settings.router_host}:{self._settings.router_port}"
        if router_url:
            api_base_url = self._router_api_base(router_url, agent)
            payload["apiBaseUrl"] = api_base_url

        logger.info(
            "agent_api_request",
            sandbox_id=sandbox_id,
            agent=agent,
            model=model,
            prompt_length=len(prompt),
            max_duration=max_duration,
            router_url=router_url,
            api_base_url=payload.get("apiBaseUrl"),
        )

        try:
            # Use streaming request for SSE
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers={
                    **self._get_headers(),
                    "Accept": "text/event-stream",
                },
                timeout=httpx.Timeout(
                    connect=30.0,
                    read=float(self._settings.http_client_timeout),
                    write=30.0,
                    pool=30.0,
                ),
            ) as response:
                if response.status_code != 200:
                    error_text = ""
                    async for chunk in response.aiter_text():
                        error_text += chunk
                    logger.error(
                        "agent_api_error",
                        status_code=response.status_code,
                        error=error_text[:500],
                    )
                    yield {
                        "type": "error",
                        "error": f"Agent API returned {response.status_code}: {error_text[:200]}",
                    }
                    return

                # Process SSE stream
                buffer = ""
                event_count = 0
                stop_stream = False
                async for chunk in response.aiter_text():
                    buffer += chunk
                    # Process complete events (lines ending with double newline)
                    while "\n\n" in buffer:
                        event_end = buffer.index("\n\n")
                        event_data = buffer[:event_end]
                        buffer = buffer[event_end + 2:]

                        for line in event_data.split("\n"):
                            if not line.startswith("data: "):
                                continue
                            data = line[6:]
                            try:
                                parsed = json.loads(data)
                                event_count += 1
                                event_type = parsed.get("type", "unknown")
                                if agent == "codex":
                                    stdout = parsed.get("stdout")
                                    stderr = parsed.get("stderr")
                                    if stdout or stderr:
                                        logger.info(
                                            "codex_agent_io",
                                            event_type=event_type,
                                            stdout_preview=str(stdout)[:300] if stdout else "",
                                            stderr_preview=str(stderr)[:300] if stderr else "",
                                        )
                                # Log detailed event info for debugging
                                logger.info(
                                    "agent_api_event",
                                    event_count=event_count,
                                    event_type=event_type,
                                    event_keys=list(parsed.keys()) if isinstance(parsed, dict) else None,
                                    event_preview=str(parsed)[:500],
                                )
                                logger.info(
                                    "agent_api_sse_event",
                                    event_count=event_count,
                                    event_type=event_type,
                                    event_keys=list(parsed.keys()) if isinstance(parsed, dict) else None,
                                    event_preview=str(parsed)[:500],
                                )
                                if event_type == "complete":
                                    logger.info(
                                        "agent_api_complete",
                                        event_count=event_count,
                                        success=parsed.get("success"),
                                        exit_code=parsed.get("exitCode"),
                                        duration=parsed.get("duration"),
                                    )
                                    stop_stream = True
                                yield parsed
                            except json.JSONDecodeError:
                                # Not JSON, yield as raw output
                                if data.strip():
                                    logger.debug("agent_api_raw_data", data_preview=data[:200])
                                    yield {"type": "output", "text": data}

                        if stop_stream:
                            break

                    if stop_stream:
                        break

                if stop_stream:
                    return

                # Process any remaining buffer
                if buffer.strip():
                    for line in buffer.split("\n"):
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        try:
                            parsed = json.loads(data)
                            event_count += 1
                            event_type = parsed.get("type", "unknown")
                            if agent == "codex":
                                stdout = parsed.get("stdout")
                                stderr = parsed.get("stderr")
                                if stdout or stderr:
                                    logger.info(
                                        "codex_agent_io",
                                        event_type=event_type,
                                        stdout_preview=str(stdout)[:300] if stdout else "",
                                        stderr_preview=str(stderr)[:300] if stderr else "",
                                    )
                            logger.info(
                                "agent_api_sse_event",
                                event_count=event_count,
                                event_type=event_type,
                                event_keys=list(parsed.keys()) if isinstance(parsed, dict) else None,
                                event_preview=str(parsed)[:500],
                            )
                            if event_type == "complete":
                                logger.info(
                                    "agent_api_complete",
                                    event_count=event_count,
                                    success=parsed.get("success"),
                                    exit_code=parsed.get("exitCode"),
                                    duration=parsed.get("duration"),
                                )
                            yield parsed
                        except json.JSONDecodeError:
                            if data.strip():
                                yield {"type": "output", "text": data}

        except httpx.TimeoutException as e:
            logger.error("agent_api_timeout", error=str(e))
            yield {"type": "error", "error": f"Agent execution timed out: {e}"}
        except Exception as e:
            logger.error("agent_api_exception", error=str(e))
            yield {"type": "error", "error": f"Agent execution failed: {e}"}

    async def _run_agent_via_api_with_retry(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        agent: str,
        model: str,
        task: str,
        *,
        request: ChatCompletionRequest,
        public_url: str | None,
        has_images: bool,
        max_duration: int,
        max_retries: int,
    ) -> AsyncGenerator[dict[str, Any], None]:
        attempt = 0
        while True:
            error_event: dict[str, Any] | None = None
            async for event in self._run_agent_via_api(
                client,
                sandbox_id,
                agent,
                model,
                task,
                request=request,
                public_url=public_url,
                has_images=has_images,
                max_duration=max_duration,
            ):
                if event.get("type") == "error":
                    error_event = event
                    continue
                yield event

            if error_event:
                error_message = str(error_event.get("error") or "Unknown error")
                if _is_timeout_error(error_message) and attempt < max_retries:
                    yield {
                        "type": "retry",
                        "error": error_message,
                        "attempt": attempt + 1,
                    }
                    await asyncio.sleep(2 ** attempt)
                    attempt += 1
                    continue
                yield error_event
            break

    def _select_agent_for_api(self, requested_agent: str | None = None) -> str:
        """Select agent for Sandy's agent/run API.

        Sandy supports these agents:
        - claude-code: Claude Code CLI (--permission-mode acceptEdits)
        - codex: OpenAI Codex CLI (--ask-for-approval never)
        - aider: Aider AI pair programmer (--yes --no-git --no-auto-commits)
        - opencode: Factory OpenCode agent
        - openhands: OpenHands devin-like agent
        - droid: Droid agent
        """
        requested = self._normalize_agent_name(requested_agent or self._baseline_agent)
        if requested in {"claude", "claude-code"}:
            agent = "claude-code"
        elif requested == "codex":
            agent = "codex"
        elif requested == "aider":
            agent = "aider"
        elif requested == "opencode":
            agent = "opencode"
        elif requested == "openhands":
            agent = "openhands"
        elif requested == "droid":
            agent = "droid"
        else:
            # Default to claude-code - has shell execution for web search, downloads, etc.
            # Note: Aider can only edit files, it cannot execute commands
            agent = "claude-code"

        logger.info(
            "agent_selection",
            requested=requested,
            selected=agent,
            config_baseline_agent=self._baseline_agent,
            requested_override=requested_agent,
        )
        return agent

    def _select_model_for_api(
        self, request: ChatCompletionRequest, agent: str | None = None
    ) -> str:
        """Select model for Sandy's agent/run API.

        Supported models on Chutes include:
        - MiniMaxAI/MiniMax-M2.1-TEE (default, fast, good tool call support)
        - deepseek-ai/DeepSeek-V3-0324-TEE (powerful but has tool call parsing issues)
        - zai-org/GLM-4.7-TEE (Chinese model, good for general tasks)
        - Qwen/Qwen3-VL-235B-A22B-Instruct (for vision tasks)
        - chutesai/Mistral-Small-3.2-24B-Instruct-2506 (fast, small)
        """
        # Use the model from request, or default to a good model
        model = request.model
        agent_name = self._normalize_agent_name(agent or self._baseline_agent)
        decision = decision_from_metadata(request.metadata)
        if decision:
            selected = model_for_decision(decision)
            logger.info(
                "model_selection",
                requested=model,
                selected=selected,
                reason="routing_decision",
            )
            return selected

        if agent_name in {"claude", "claude-code"}:
            # Claude Code uses Anthropic Messages format; route through Janus router by default.
            return self._settings.effective_model or CLAUDE_AGENT_DEFAULT_MODEL

        # Sandy's agent API expects certain model formats
        # Skip generic baseline aliases
        if model in {"baseline", "janus-router", "janus-baseline"}:
            # Use MiniMax as default - DeepSeek has issues with tool call parsing
            # in Sandy's agent runner (causes "'dict object' has no attribute 'name'" errors)
            selected = "MiniMaxAI/MiniMax-M2.1-TEE"
            logger.info(
                "model_selection",
                requested=model,
                selected=selected,
                reason="baseline_alias_default",
            )
            return selected

        # Pass through specific model names
        if model.startswith("gpt-") or model.startswith("o1-") or model.startswith("o3-"):
            logger.info(
                "model_selection",
                requested=model,
                selected=model,
                reason="openai_model_passthrough",
            )
            return model
        if "claude" in model.lower():
            logger.info(
                "model_selection",
                requested=model,
                selected=model,
                reason="claude_model_passthrough",
            )
            return model
        if "/" in model:  # Looks like a Chutes model path
            logger.info(
                "model_selection",
                requested=model,
                selected=model,
                reason="chutes_model_passthrough",
            )
            return model

        # Default model for general use - use MiniMax which has better tool call support
        selected = "MiniMaxAI/MiniMax-M2.1-TEE"
        logger.info(
            "model_selection",
            requested=model,
            selected=selected,
            reason="default_fallback",
        )
        return selected

    def _generate_id(self) -> str:
        """Generate a completion ID."""
        return f"chatcmpl-baseline-sandy-{uuid.uuid4().hex[:12]}"

    def _build_agent_prompt(
        self,
        user_message: str,
        flags: GenerationFlags | None,
    ) -> str:
        instructions: list[str] = []

        if flags:
            if flags.generate_image:
                instructions.append(
                    "The user has explicitly requested IMAGE GENERATION. "
                    "You MUST generate one or more images as part of your response using the Chutes image API."
                )
            if flags.generate_video:
                instructions.append(
                    "The user has explicitly requested VIDEO GENERATION. "
                    "You MUST generate a video as part of your response using the Chutes video API."
                )
            if flags.generate_audio:
                instructions.append(
                    "The user has explicitly requested AUDIO GENERATION. "
                    "You MUST generate audio (speech/music) as part of your response using the Chutes TTS/audio API."
                )
            if flags.deep_research:
                instructions.append(
                    "The user has explicitly requested DEEP RESEARCH. "
                    "You MUST perform comprehensive research with citations using chutes-search max mode."
                )
            if flags.web_search:
                instructions.append(
                    "The user has explicitly requested WEB SEARCH. "
                    "You MUST search the internet for current information to answer this query."
                )

        if not instructions:
            return user_message

        instruction_block = "\n".join(f"- {instruction}" for instruction in instructions)

        return (
            "______ Generation Instructions ______\n"
            "The user has enabled the following generation modes:\n"
            f"{instruction_block}\n\n"
            "Please ensure your response includes the requested generated content.\n"
            "_____________________________________\n\n"
            f"{user_message}"
        )

    def _extract_task(self, request: ChatCompletionRequest) -> str:
        """Extract the task description from the request."""
        for msg in reversed(request.messages):
            if msg.role.value == "user" and msg.content:
                task_text = ""
                image_urls = get_image_urls(msg)

                if isinstance(msg.content, str):
                    task_text = msg.content
                else:
                    # Handle list of content parts
                    for part in msg.content:
                        if hasattr(part, "text"):
                            task_text = part.text
                            break
                        elif isinstance(part, dict) and part.get("type") == "text":
                            task_text = part.get("text", "")
                            break

                if image_urls:
                    task_text = task_text or "Image analysis request"
                    task_text += (
                        f"\n\n[{len(image_urls)} image(s) attached - "
                        "use vision capabilities to analyze]"
                    )

                return self._build_agent_prompt(task_text, request.generation_flags)
        return "No task specified"

    @log_function_call
    async def complete(
        self,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
        baseline_agent_override: str | None = None,
    ) -> ChatCompletionResponse:
        """Execute a complex task and return a non-streaming response."""
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)
        has_images = contains_images(request.messages)

        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.SANDBOX_INIT,
                "SANDY",
                "Starting sandbox execution",
                data={"has_images": has_images},
            )

        if not self.is_available:
            content = (
                "I would execute this complex task in a Sandy sandbox:\n\n"
                f"**Task:** {task}\n\nSandy is not currently configured, "
                "so I cannot execute code. Please configure SANDY_BASE_URL "
                "to enable sandbox execution."
            )
            return ChatCompletionResponse(
                id=request_id,
                model=model,
                choices=[
                    Choice(
                        message=AssistantMessage(
                            role="assistant",
                            content=content,
                        ),
                        finish_reason=FinishReason.STOP,
                    )
                ],
            )

        sandbox_start = time.perf_counter()

        async with self._client_factory() as client:
            sandbox_info = await self._create_sandbox(client)
            if not sandbox_info:
                return ChatCompletionResponse(
                    id=request_id,
                    model=model,
                    choices=[
                        Choice(
                            message=AssistantMessage(
                                role="assistant",
                                content="Error: Failed to create sandbox.",
                            ),
                            finish_reason=FinishReason.STOP,
                        )
                    ],
                )

            sandbox_id, public_url = sandbox_info
            sandbox_url = self._sandbox_url(sandbox_id, public_url)
            artifacts_present = False
            artifacts: list[Artifact] = []

            try:
                if not await self._upload_agent_pack(client, sandbox_id):
                    return ChatCompletionResponse(
                        id=request_id,
                        model=model,
                        choices=[
                            Choice(
                                message=AssistantMessage(
                                    role="assistant",
                                    content=(
                                        "Error: Failed to upload agent pack to sandbox."
                                    ),
                                ),
                                finish_reason=FinishReason.STOP,
                            )
                        ],
                    )

                bootstrap_stdout, bootstrap_stderr, bootstrap_exit = await self._run_bootstrap(
                    client, sandbox_id, public_url, request, has_images
                )
                if bootstrap_exit != 0:
                    error_detail = bootstrap_stderr or "Bootstrap failed."
                    return ChatCompletionResponse(
                        id=request_id,
                        model=model,
                        choices=[
                            Choice(
                                message=AssistantMessage(
                                    role="assistant",
                                    content=error_detail,
                                ),
                                finish_reason=FinishReason.STOP,
                            )
                        ],
                    )

                if bootstrap_stdout:
                    logger.info("sandy_bootstrap_output", stdout=bootstrap_stdout)

                selected_agent = await self._select_agent(
                    client, sandbox_id, baseline_agent_override
                )
                if debug_emitter:
                    await debug_emitter.emit(
                        DebugEventType.AGENT_THINKING,
                        "AGENT",
                        f"Selected CLI agent: {selected_agent}",
                        data={"agent": selected_agent},
                    )
                command = self._build_agent_command(
                    selected_agent, task, sandbox_id, public_url, request, has_images
                )
                stdout, stderr, exit_code = await self._exec_in_sandbox(
                    client, sandbox_id, command
                )

                result = stdout.strip() if stdout else ""
                if not result:
                    result = "Agent returned no output."
                if stderr:
                    result = f"{result}\n\nErrors:\n{stderr.strip()}"

                artifacts = await self._collect_artifacts(
                    client, sandbox_id, public_url
                )
                artifacts_present = bool(artifacts)
                if artifacts:
                    links = self._format_artifact_links(artifacts)
                    result = f"{result}\n\nArtifacts available:\n{links}"

                result = process_agent_response(result, sandbox_url)

                return ChatCompletionResponse(
                    id=request_id,
                    model=model,
                    choices=[
                        Choice(
                            message=AssistantMessage(
                                role="assistant",
                                content=result,
                                artifacts=artifacts or None,
                            ),
                            finish_reason=FinishReason.STOP,
                        )
                    ],
                    usage=Usage(
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        sandbox_seconds=time.perf_counter() - sandbox_start,
                    ),
                )

            finally:
                if artifacts_present and self._artifact_grace_seconds > 0:
                    logger.info(
                        "sandy_terminate_delayed",
                        sandbox_id=sandbox_id,
                        delay_seconds=self._artifact_grace_seconds,
                    )
                    self._schedule_sandbox_termination(
                        sandbox_id, self._artifact_grace_seconds
                    )
                else:
                    await self._terminate_sandbox(client, sandbox_id)

    async def execute_complex(
        self,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
        baseline_agent_override: str | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Execute a complex task using Sandy sandbox."""
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)
        has_images = contains_images(request.messages)

        # Emit initial role
        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
        )

        # Emit reasoning: starting
        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[
                ChunkChoice(
                    delta=Delta(reasoning_content="Starting complex task execution...\n")
                )
            ],
        )

        if not self.is_available:
            # Sandy not configured - return a mock response
            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.ERROR,
                    "SANDY",
                    "Sandy is not configured",
                )
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[
                    ChunkChoice(
                        delta=Delta(
                            reasoning_content=(
                                "Note: Sandy is not configured. Running in mock mode.\n"
                            )
                        )
                    )
                ],
            )
            await asyncio.sleep(0.5)

            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[
                    ChunkChoice(
                        delta=Delta(
                            content=(
                                "I would execute this complex task in a Sandy sandbox:\n\n"
                                f"**Task:** {task}\n\nSandy is not currently configured, "
                                "so I cannot execute code. Please configure SANDY_BASE_URL "
                                "to enable sandbox execution."
                            )
                        )
                    )
                ],
            )

            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)],
            )
            return

        # Create sandbox
        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[
                ChunkChoice(delta=Delta(reasoning_content="Creating Sandy sandbox...\n"))
            ],
        )

        sandbox_start = time.perf_counter()

        async with self._client_factory() as client:
            sandbox_info = await self._create_sandbox(client)

            if not sandbox_info:
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(content="Error: Failed to create sandbox.")
                        )
                    ],
                )
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                    ],
                )
                return

            sandbox_id, public_url = sandbox_info
            sandbox_url = self._sandbox_url(sandbox_id, public_url)
            artifacts: list[Artifact] = []

            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.AGENT_THINKING,
                    "AGENT",
                    f"Sandbox created: {sandbox_id}",
                )

            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[
                    ChunkChoice(
                        delta=Delta(
                            reasoning_content=f"Sandbox created: {sandbox_id}\n"
                        )
                    )
                ],
            )

            try:
                if not self._system_prompt_path.exists():
                    logger.warning(
                        "system_prompt_missing", path=str(self._system_prompt_path)
                    )

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(reasoning_content="Uploading agent pack...\n")
                        )
                    ],
                )

                if not await self._upload_agent_pack(client, sandbox_id):
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    content="Error: Failed to upload agent pack to sandbox."
                                )
                            )
                        ],
                    )
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                        ],
                    )
                    return

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(reasoning_content="Running agent pack bootstrap...\n")
                        )
                    ],
                )

                bootstrap_stdout, bootstrap_stderr, bootstrap_exit = await self._run_bootstrap(
                    client, sandbox_id, public_url, request, has_images
                )
                if bootstrap_exit != 0:
                    error_detail = bootstrap_stderr or "Bootstrap failed."
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[ChunkChoice(delta=Delta(content=error_detail))],
                    )
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                        ],
                    )
                    return

                if bootstrap_stdout:
                    trimmed_bootstrap = _trim_bootstrap_output(bootstrap_stdout)
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    reasoning_content=f"{trimmed_bootstrap.rstrip()}\n"
                                )
                            )
                        ],
                    )

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(reasoning_content="Selecting CLI agent...\n")
                        )
                    ],
                )

                selected_agent = await self._select_agent(
                    client, sandbox_id, baseline_agent_override
                )
                if debug_emitter:
                    await debug_emitter.emit(
                        DebugEventType.AGENT_THINKING,
                        "AGENT",
                        f"Selected CLI agent: {selected_agent}",
                        data={"agent": selected_agent},
                    )
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(
                                reasoning_content=f"Launching CLI agent ({selected_agent})...\n"
                            )
                        )
                    ],
                )

                command = self._build_agent_command(
                    selected_agent, task, sandbox_id, public_url, request, has_images
                )
                agent_task = asyncio.create_task(
                    self._exec_in_sandbox(client, sandbox_id, command)
                )
                screenshot_seen: set[str] = set()
                poll_interval = 0.5

                while True:
                    try:
                        await asyncio.wait_for(asyncio.shield(agent_task), timeout=poll_interval)
                        break
                    except asyncio.TimeoutError:
                        pass

                    for event in await self._collect_screenshot_events(
                        client, sandbox_id, screenshot_seen, request_id, model
                    ):
                        yield event

                stdout, stderr, exit_code = await agent_task
                for event in await self._collect_screenshot_events(
                    client, sandbox_id, screenshot_seen, request_id, model
                ):
                    yield event

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(
                                reasoning_content=(
                                    "Agent execution complete "
                                    f"(exit code: {exit_code})\n"
                                )
                            )
                        )
                    ],
                )
                if debug_emitter:
                    await debug_emitter.emit(
                        DebugEventType.RESPONSE_COMPLETE,
                        "SSE",
                        f"Agent execution complete (exit code: {exit_code})",
                        data={"exit_code": exit_code},
                    )

                result = stdout.strip() if stdout else ""
                if not result:
                    result = "Agent returned no output."
                if stderr:
                    result = f"{result}\n\nErrors:\n{stderr.strip()}"

                result = process_agent_response(result, sandbox_url)

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[ChunkChoice(delta=Delta(content=result))],
                )

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(reasoning_content="Collecting artifacts...\n")
                        )
                    ],
                )
                artifacts = await self._collect_artifacts(
                    client, sandbox_id, public_url
                )
                artifacts_present = bool(artifacts)
                if artifacts:
                    artifact_payload = [artifact.model_dump(mode="json") for artifact in artifacts]
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    janus={
                                        "event": "artifacts",
                                        "payload": {"items": artifact_payload},
                                    }
                                )
                            )
                        ],
                    )
                    links = self._format_artifact_links(artifacts)
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    content=f"\n\nArtifacts available:\n{links}"
                                )
                            )
                        ],
                    )

            finally:
                grace_seconds = (
                    self._artifact_grace_seconds if artifacts_present else 0
                )
                if grace_seconds > 0:
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    reasoning_content=(
                                        "Keeping sandbox alive for artifact downloads "
                                        f"({grace_seconds}s)...\n"
                                    )
                                )
                            )
                        ],
                    )
                    self._schedule_sandbox_termination(sandbox_id, grace_seconds)
                else:
                    # Cleanup immediately
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(reasoning_content="Terminating sandbox...\n")
                            )
                        ],
                    )
                    await self._terminate_sandbox(client, sandbox_id)

                sandbox_seconds = time.perf_counter() - sandbox_start

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                    ],
                )

                # Include usage with sandbox time
                if request.stream_options and request.stream_options.include_usage:
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[],
                        usage=Usage(
                            prompt_tokens=0,
                            completion_tokens=0,
                            total_tokens=0,
                            sandbox_seconds=sandbox_seconds,
                        ),
                    )

    @log_function_call
    async def complete_via_agent_api(
        self,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
        baseline_agent_override: str | None = None,
    ) -> ChatCompletionResponse:
        if self.requires_cli_execution(baseline_agent_override):
            return await self.complete(
                request,
                debug_emitter=debug_emitter,
                baseline_agent_override=baseline_agent_override,
            )
        """
        Execute a task using Sandy's agent/run API and return a non-streaming response.

        This collects all streaming events and returns the final result.
        """
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)
        has_images = contains_images(request.messages)

        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.SANDBOX_INIT,
                "SANDY",
                "Starting sandbox execution",
                data={"has_images": has_images},
            )

        if not self.is_available:
            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.ERROR,
                    "SANDY",
                    "Sandy is not configured",
                )
            content = (
                "I would execute this task in a Sandy sandbox:\n\n"
                f"**Task:** {task}\n\nSandy is not currently configured. "
                "Please configure SANDY_BASE_URL to enable sandbox execution."
            )
            return ChatCompletionResponse(
                id=request_id,
                model=model,
                choices=[
                    Choice(
                        message=AssistantMessage(
                            role="assistant",
                            content=content,
                        ),
                        finish_reason=FinishReason.STOP,
                    )
                ],
            )

        agent = self._select_agent_for_api(baseline_agent_override)
        api_model = self._select_model_for_api(request, agent=agent)
        start_message = (
            "Starting claude-code agent with intelligent model routing among Chutes models"
            if agent in {"claude", "claude-code"}
            else f"Starting {agent} agent in Sandy sandbox"
        )
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.AGENT_THINKING,
                "AGENT",
                start_message,
                data={"agent": agent, "model": api_model},
            )
        sandbox_start = time.perf_counter()
        output_parts: list[str] = []
        recovered_output_parts: list[str] = []
        seen_tool_results: set[str] = set()

        async with self._client_factory() as client:
            sandbox_info = await self._create_sandbox(client)
            if not sandbox_info:
                if debug_emitter:
                    await debug_emitter.emit(
                        DebugEventType.ERROR,
                        "SANDY",
                        "Failed to create sandbox",
                    )
                return ChatCompletionResponse(
                    id=request_id,
                    model=model,
                    choices=[
                        Choice(
                            message=AssistantMessage(
                                role="assistant",
                                content="Error: Failed to create sandbox.",
                            ),
                            finish_reason=FinishReason.STOP,
                        )
                    ],
                )

            sandbox_id, public_url = sandbox_info
            sandbox_url = self._sandbox_url(sandbox_id, public_url)
            artifacts: list[Artifact] = []

            try:
                if not self._system_prompt_path.exists():
                    logger.warning(
                        "system_prompt_missing", path=str(self._system_prompt_path)
                    )

                if not await self._upload_agent_pack(client, sandbox_id):
                    return ChatCompletionResponse(
                        id=request_id,
                        model=model,
                        choices=[
                            Choice(
                                message=AssistantMessage(
                                    role="assistant",
                                    content="Error: Failed to upload agent pack to sandbox.",
                                ),
                                finish_reason=FinishReason.STOP,
                            )
                        ],
                    )

                bootstrap_stdout, bootstrap_stderr, bootstrap_exit = await self._run_bootstrap(
                    client, sandbox_id, public_url, request, has_images
                )
                if bootstrap_exit != 0:
                    error_detail = bootstrap_stderr or "Bootstrap failed."
                    return ChatCompletionResponse(
                        id=request_id,
                        model=model,
                        choices=[
                            Choice(
                                message=AssistantMessage(
                                    role="assistant",
                                    content=error_detail,
                                ),
                                finish_reason=FinishReason.STOP,
                            )
                        ],
                    )

                if bootstrap_stdout:
                    logger.info(
                        "sandy_bootstrap_output",
                        stdout=bootstrap_stdout,
                    )

                async for event in self._run_agent_via_api_with_retry(
                    client,
                    sandbox_id,
                    agent,
                    api_model,
                    task,
                    request=request,
                    public_url=public_url,
                    has_images=has_images,
                    max_duration=self._timeout,
                    max_retries=2,
                ):
                    event_type = event.get("type", "")

                    if event_type == "output":
                        text = _strip_ansi(event.get("text", ""))
                        if text:
                            filtered_text = _filter_agent_message(text)
                            if filtered_text:
                                tool_result_path = _extract_tool_result_path(filtered_text)
                                if tool_result_path and tool_result_path not in seen_tool_results:
                                    seen_tool_results.add(tool_result_path)
                                    recovered_text = await self._read_tool_result_text(
                                        client, sandbox_id, tool_result_path
                                    )
                                    if recovered_text:
                                        recovered_text = await self._materialize_data_url_images(
                                            client, sandbox_id, recovered_text
                                        )
                                        recovered_text = process_agent_response(
                                            recovered_text, sandbox_url
                                        )
                                        recovered_output_parts.append(recovered_text)
                                output_parts.append(filtered_text)

                    elif event_type == "agent-output":
                        data = event.get("data", {})
                        if isinstance(data, dict):
                            msg_type = data.get("type", "")
                            if msg_type == "stream_event":
                                event_payload = data.get("event", {})
                                delta = {}
                                if isinstance(event_payload, dict):
                                    delta = event_payload.get("delta", {}) if isinstance(event_payload.get("delta"), dict) else {}
                                if not delta and isinstance(data.get("delta"), dict):
                                    delta = data.get("delta", {})
                                text = None
                                if isinstance(delta, dict):
                                    text = delta.get("text") or delta.get("content")
                                if not text and isinstance(event_payload, dict):
                                    text = event_payload.get("text") or event_payload.get("content")
                                if not text:
                                    text = data.get("text")
                                if isinstance(text, str) and text:
                                    filtered_text = _filter_agent_message(text)
                                    if filtered_text:
                                        output_parts.append(filtered_text)
                            elif msg_type == "result":
                                result_text = data.get("result") or data.get("text")
                                if isinstance(result_text, str) and result_text:
                                    filtered_text = _filter_agent_message(result_text)
                                    if filtered_text:
                                        output_parts.append(filtered_text)
                            elif msg_type == "assistant":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text = block.get("text", "")
                                            if text:
                                                filtered_text = _filter_agent_message(text)
                                                if filtered_text:
                                                    output_parts.append(filtered_text)
                            elif msg_type == "user":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "tool_result":
                                            tool_content = block.get("content", "")
                                            if not isinstance(tool_content, str) or not tool_content.strip():
                                                continue
                                            tool_result_path = _extract_tool_result_path(tool_content)
                                            if tool_result_path and tool_result_path not in seen_tool_results:
                                                seen_tool_results.add(tool_result_path)
                                                recovered_text = await self._read_tool_result_text(
                                                    client, sandbox_id, tool_result_path
                                                )
                                                if recovered_text:
                                                    recovered_text = await self._materialize_data_url_images(
                                                        client, sandbox_id, recovered_text
                                                    )
                                                    recovered_text = process_agent_response(
                                                        recovered_text, sandbox_url
                                                    )
                                                    recovered_output_parts.append(recovered_text)

                    elif event_type == "stream_event":
                        event_payload = event.get("event", {})
                        delta = {}
                        if isinstance(event_payload, dict):
                            delta = event_payload.get("delta", {}) if isinstance(event_payload.get("delta"), dict) else {}
                        if not delta and isinstance(event.get("delta"), dict):
                            delta = event.get("delta", {})
                        text = None
                        if isinstance(delta, dict):
                            text = delta.get("text") or delta.get("content")
                        if not text and isinstance(event_payload, dict):
                            text = event_payload.get("text") or event_payload.get("content")
                        if not text:
                            text = event.get("text")
                        if isinstance(text, str) and text:
                            filtered_text = _filter_agent_message(text)
                            if filtered_text:
                                output_parts.append(filtered_text)

                    elif event_type == "result":
                        result_text = event.get("result") or event.get("text")
                        if isinstance(result_text, str) and result_text:
                            filtered_text = _filter_agent_message(result_text)
                            if filtered_text:
                                output_parts.append(filtered_text)

                    elif event_type == "error":
                        error_msg = _format_agent_error(
                            str(event.get("error", "Unknown error"))
                        )
                        output_parts.append(f"Error: {error_msg}")

                if output_parts:
                    result = "\n".join(output_parts)
                elif recovered_output_parts:
                    result = "\n".join(recovered_output_parts)
                else:
                    result = "Agent completed without output."
                # Clean up Aider-specific output formatting
                result = _clean_aider_output(result)
                result = process_agent_response(result, sandbox_url)

                artifacts = await self._collect_artifacts(client, sandbox_id, public_url)
                artifacts_present = bool(artifacts)
                if artifacts:
                    links = self._format_artifact_links(artifacts)
                    result = f"{result}\n\nArtifacts available:\n{links}"

                response_payload = ChatCompletionResponse(
                    id=request_id,
                    model=model,
                    choices=[
                        Choice(
                            message=AssistantMessage(
                                role="assistant",
                                content=result,
                                artifacts=artifacts or None,
                            ),
                            finish_reason=FinishReason.STOP,
                        )
                    ],
                    usage=Usage(
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        sandbox_seconds=time.perf_counter() - sandbox_start,
                    ),
                )

                if debug_emitter:
                    await debug_emitter.emit(
                        DebugEventType.RESPONSE_COMPLETE,
                        "SSE",
                        "Response complete",
                    )

                return response_payload

            finally:
                if artifacts_present and self._artifact_grace_seconds > 0:
                    logger.info(
                        "sandy_terminate_delayed",
                        sandbox_id=sandbox_id,
                        delay_seconds=self._artifact_grace_seconds,
                    )
                    self._schedule_sandbox_termination(
                        sandbox_id, self._artifact_grace_seconds
                    )
                else:
                    await self._terminate_sandbox(client, sandbox_id)

    async def complete_via_agent_api_in_sandbox(
        self,
        sandbox_id: str,
        public_url: str | None,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
        baseline_agent_override: str | None = None,
        run_state: dict[str, Any] | None = None,
        terminate_on_finish: bool = False,
    ) -> ChatCompletionResponse:
        """Execute a task using an existing warmed sandbox."""
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)
        has_images = contains_images(request.messages)

        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.SANDBOX_INIT,
                "SANDY",
                "Starting sandbox execution",
                data={"warm_pool": True},
            )

        if not self.is_available:
            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.ERROR,
                    "SANDY",
                    "Sandy is not configured",
                )
            content = (
                "I would execute this task in a Sandy sandbox:\n\n"
                f"**Task:** {task}\n\nSandy is not currently configured. "
                "Please configure SANDY_BASE_URL to enable sandbox execution."
            )
            return ChatCompletionResponse(
                id=request_id,
                model=model,
                choices=[
                    Choice(
                        message=AssistantMessage(
                            role="assistant",
                            content=content,
                        ),
                        finish_reason=FinishReason.STOP,
                    )
                ],
            )

        agent = self._select_agent_for_api(baseline_agent_override)
        api_model = self._select_model_for_api(request, agent=agent)
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.AGENT_THINKING,
                "AGENT",
                "Using warm sandbox for agent execution",
                data={"agent": agent, "model": api_model, "sandbox_id": sandbox_id},
            )

        sandbox_start = time.perf_counter()
        output_parts: list[str] = []
        recovered_output_parts: list[str] = []
        seen_tool_results: set[str] = set()
        has_error = False
        exit_code = 0
        artifacts_present = False
        termination_scheduled = False

        async with self._client_factory() as client:
            sandbox_url = self._sandbox_url(sandbox_id, public_url)
            try:
                if not self._system_prompt_path.exists():
                    logger.warning(
                        "system_prompt_missing", path=str(self._system_prompt_path)
                    )

                async for event in self._run_agent_via_api_with_retry(
                    client,
                    sandbox_id,
                    agent,
                    api_model,
                    task,
                    request=request,
                    public_url=public_url,
                    has_images=has_images,
                    max_duration=self._timeout,
                    max_retries=2,
                ):
                    event_type = event.get("type", "")

                    if event_type == "output":
                        text = _strip_ansi(event.get("text", ""))
                        if text:
                            filtered_text = _filter_agent_message(text)
                            if filtered_text:
                                tool_result_path = _extract_tool_result_path(filtered_text)
                                if tool_result_path and tool_result_path not in seen_tool_results:
                                    seen_tool_results.add(tool_result_path)
                                    recovered_text = await self._read_tool_result_text(
                                        client, sandbox_id, tool_result_path
                                    )
                                    if recovered_text:
                                        recovered_text = await self._materialize_data_url_images(
                                            client, sandbox_id, recovered_text
                                        )
                                        recovered_text = process_agent_response(
                                            recovered_text, sandbox_url
                                        )
                                        recovered_output_parts.append(recovered_text)
                                output_parts.append(filtered_text)

                    elif event_type == "agent-output":
                        data = event.get("data", {})
                        if isinstance(data, dict):
                            msg_type = data.get("type", "")
                            if msg_type == "stream_event":
                                event_payload = data.get("event", {})
                                delta = {}
                                if isinstance(event_payload, dict):
                                    delta = event_payload.get("delta", {}) if isinstance(event_payload.get("delta"), dict) else {}
                                if not delta and isinstance(data.get("delta"), dict):
                                    delta = data.get("delta", {})
                                text = None
                                if isinstance(delta, dict):
                                    text = delta.get("text") or delta.get("content")
                                if not text and isinstance(event_payload, dict):
                                    text = event_payload.get("text") or event_payload.get("content")
                                if not text:
                                    text = data.get("text")
                                if isinstance(text, str) and text:
                                    filtered_text = _filter_agent_message(text)
                                    if filtered_text:
                                        output_parts.append(filtered_text)
                            elif msg_type == "result":
                                result_text = data.get("result") or data.get("text")
                                if isinstance(result_text, str) and result_text:
                                    filtered_text = _filter_agent_message(result_text)
                                    if filtered_text:
                                        output_parts.append(filtered_text)
                            elif msg_type == "assistant":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text = block.get("text", "")
                                            if text:
                                                filtered_text = _filter_agent_message(text)
                                                if filtered_text:
                                                    output_parts.append(filtered_text)
                            elif msg_type == "user":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "tool_result":
                                            tool_content = block.get("content", "")
                                            if not isinstance(tool_content, str) or not tool_content.strip():
                                                continue
                                            tool_result_path = _extract_tool_result_path(tool_content)
                                            if tool_result_path and tool_result_path not in seen_tool_results:
                                                seen_tool_results.add(tool_result_path)
                                                recovered_text = await self._read_tool_result_text(
                                                    client, sandbox_id, tool_result_path
                                                )
                                                if recovered_text:
                                                    recovered_text = await self._materialize_data_url_images(
                                                        client, sandbox_id, recovered_text
                                                    )
                                                    recovered_text = process_agent_response(
                                                        recovered_text, sandbox_url
                                                    )
                                                    recovered_output_parts.append(recovered_text)

                    elif event_type == "stream_event":
                        event_payload = event.get("event", {})
                        delta = {}
                        if isinstance(event_payload, dict):
                            delta = event_payload.get("delta", {}) if isinstance(event_payload.get("delta"), dict) else {}
                        if not delta and isinstance(event.get("delta"), dict):
                            delta = event.get("delta", {})
                        text = None
                        if isinstance(delta, dict):
                            text = delta.get("text") or delta.get("content")
                        if not text and isinstance(event_payload, dict):
                            text = event_payload.get("text") or event_payload.get("content")
                        if not text:
                            text = event.get("text")
                        if isinstance(text, str) and text:
                            filtered_text = _filter_agent_message(text)
                            if filtered_text:
                                output_parts.append(filtered_text)

                    elif event_type == "result":
                        result_text = event.get("result") or event.get("text")
                        if isinstance(result_text, str) and result_text:
                            filtered_text = _filter_agent_message(result_text)
                            if filtered_text:
                                output_parts.append(filtered_text)

                    elif event_type == "complete":
                        exit_code = event.get("exitCode", 0)

                    elif event_type == "error":
                        error_msg = _format_agent_error(
                            str(event.get("error", "Unknown error"))
                        )
                        has_error = True
                        output_parts.append(f"Error: {error_msg}")

                if output_parts:
                    result = "\n".join(output_parts)
                elif recovered_output_parts:
                    result = "\n".join(recovered_output_parts)
                else:
                    result = "Agent completed without output."
                result = _clean_aider_output(result)
                result = process_agent_response(result, sandbox_url)

                artifacts = await self._collect_artifacts(client, sandbox_id, public_url)
                artifacts_present = bool(artifacts)
                if artifacts:
                    links = self._format_artifact_links(artifacts)
                    result = f"{result}\n\nArtifacts available:\n{links}"

                response_payload = ChatCompletionResponse(
                    id=request_id,
                    model=model,
                    choices=[
                        Choice(
                            message=AssistantMessage(
                                role="assistant",
                                content=result,
                                artifacts=artifacts or None,
                            ),
                            finish_reason=FinishReason.STOP,
                        )
                    ],
                    usage=Usage(
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        sandbox_seconds=time.perf_counter() - sandbox_start,
                    ),
                )

                if debug_emitter:
                    await debug_emitter.emit(
                        DebugEventType.RESPONSE_COMPLETE,
                        "SSE",
                        "Response complete",
                    )

                return response_payload

            finally:
                if artifacts_present and self._artifact_grace_seconds > 0:
                    logger.info(
                        "sandy_terminate_delayed",
                        sandbox_id=sandbox_id,
                        delay_seconds=self._artifact_grace_seconds,
                    )
                    self._schedule_sandbox_termination(
                        sandbox_id, self._artifact_grace_seconds
                    )
                    termination_scheduled = True
                elif terminate_on_finish or has_error:
                    await self._terminate_sandbox(client, sandbox_id)

                if run_state is not None:
                    run_state.update(
                        {
                            "has_error": has_error,
                            "exit_code": exit_code,
                            "artifacts_present": artifacts_present,
                            "termination_scheduled": termination_scheduled,
                        }
                    )

    async def execute_via_agent_api(
        self,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
        baseline_agent_override: str | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Execute a task using Sandy's built-in agent/run API.

        This is the preferred method as it:
        - Uses Sandy's pre-configured agent settings with yolo mode
        - Handles agent setup, config files, and environment
        - Boots the agent pack to ensure docs + router are available
        - Streams real-time output from the agent
        """
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)
        has_images = contains_images(request.messages)

        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.SANDBOX_INIT,
                "SANDY",
                "Starting sandbox execution",
            )

        # Emit initial role
        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
        )

        if not self.is_available:
            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.ERROR,
                    "SANDY",
                    "Sandy is not configured",
                )
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[
                    ChunkChoice(
                        delta=Delta(
                            content=(
                                "I would execute this task in a Sandy sandbox:\n\n"
                                f"**Task:** {task}\n\nSandy is not currently configured. "
                                "Please configure SANDY_BASE_URL to enable sandbox execution."
                            )
                        )
                    )
                ],
            )
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)],
            )
            return

        # Select agent and model for Sandy's API
        agent = self._select_agent_for_api(baseline_agent_override)
        api_model = self._select_model_for_api(request, agent=agent)

        start_message = (
            "Starting claude-code agent with intelligent model routing among Chutes models"
            if agent in {"claude", "claude-code"}
            else f"Starting {agent} agent in Sandy sandbox"
        )
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.AGENT_THINKING,
                "AGENT",
                start_message,
                data={"agent": agent, "model": api_model},
            )

        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[
                ChunkChoice(
                    delta=Delta(reasoning_content=f"{start_message}...\n")
                )
            ],
        )

        sandbox_start = time.perf_counter()
        output_parts: list[str] = []
        recovered_output_parts: list[str] = []
        seen_tool_results: set[str] = set()
        long_ops_seen: set[str] = set()
        content_streamed = False  # Track if we've streamed any content
        has_error = False
        exit_code = 0

        async with self._client_factory() as client:
            # Create sandbox (Sandy's agent/run handles the rest)
            sandbox_info = await self._create_sandbox(client)

            if not sandbox_info:
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(content="Error: Failed to create sandbox.")
                        )
                    ],
                )
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                    ],
                )
                return

            sandbox_id, public_url = sandbox_info
            sandbox_url = self._sandbox_url(sandbox_id, public_url)

            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[
                    ChunkChoice(
                        delta=Delta(
                            reasoning_content=f"Sandbox created: {sandbox_id}\n"
                        )
                    )
                ],
            )

            try:
                if not self._system_prompt_path.exists():
                    logger.warning(
                        "system_prompt_missing", path=str(self._system_prompt_path)
                    )

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(reasoning_content="Uploading agent pack...\n")
                        )
                    ],
                )

                if not await self._upload_agent_pack(client, sandbox_id):
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    content="Error: Failed to upload agent pack to sandbox."
                                )
                            )
                        ],
                    )
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                        ],
                    )
                    return

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(reasoning_content="Running agent pack bootstrap...\n")
                        )
                    ],
                )

                bootstrap_stdout, bootstrap_stderr, bootstrap_exit = await self._run_bootstrap(
                    client, sandbox_id, public_url, request, has_images
                )
                if bootstrap_exit != 0:
                    error_detail = bootstrap_stderr or "Bootstrap failed."
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[ChunkChoice(delta=Delta(content=error_detail))],
                    )
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                        ],
                    )
                    return

                if bootstrap_stdout:
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    reasoning_content=f"{bootstrap_stdout.rstrip()}\n"
                                )
                            )
                        ],
                    )

                # Run agent via Sandy's API
                async for event in self._run_agent_via_api_with_retry(
                    client,
                    sandbox_id,
                    agent,
                    api_model,
                    task,
                    request=request,
                    public_url=public_url,
                    has_images=has_images,
                    max_duration=self._timeout,
                    max_retries=2,
                ):
                    event_type = event.get("type", "")

                    if event_type == "status":
                        # Progress status messages
                        message = event.get("message", "")
                        filtered_message = _filter_agent_message(message) if message else None
                        if filtered_message:
                            indicator_chunk = _build_long_operation_chunk(
                                _long_operation_indicator(filtered_message),
                                request_id,
                                model,
                                long_ops_seen,
                            )
                            if indicator_chunk:
                                yield indicator_chunk
                            if debug_emitter:
                                await debug_emitter.emit(
                                    DebugEventType.AGENT_THINKING,
                                    "AGENT",
                                    filtered_message,
                                )
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(reasoning_content=f"{filtered_message}\n")
                                    )
                                ],
                            )

                    elif event_type == "output":
                        # Text output from agent
                        text = _strip_ansi(event.get("text", ""))
                        filtered_text = _filter_agent_message(text) if text else None
                        if filtered_text:
                            indicator_chunk = _build_long_operation_chunk(
                                _long_operation_indicator(filtered_text),
                                request_id,
                                model,
                                long_ops_seen,
                            )
                            if indicator_chunk:
                                yield indicator_chunk
                            tool_result_path = _extract_tool_result_path(filtered_text)
                            if tool_result_path and tool_result_path not in seen_tool_results:
                                seen_tool_results.add(tool_result_path)
                                recovered_text = await self._read_tool_result_text(
                                    client, sandbox_id, tool_result_path
                                )
                                if recovered_text:
                                    recovered_text = await self._materialize_data_url_images(
                                        client, sandbox_id, recovered_text
                                    )
                                    recovered_text = process_agent_response(
                                        recovered_text, sandbox_url
                                    )
                                    recovered_output_parts.append(recovered_text)
                            if debug_emitter:
                                await debug_emitter.emit(
                                    DebugEventType.RESPONSE_CHUNK,
                                    "AGENT",
                                    filtered_text,
                                )
                            output_parts.append(filtered_text)
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(reasoning_content=f"{filtered_text}\n")
                                    )
                                ],
                            )

                    elif event_type == "agent-output":
                        # Structured agent output (especially from claude-code)
                        data = event.get("data", {})
                        if isinstance(data, dict):
                            # Extract content from Claude Code stream-json output
                            msg_type = data.get("type", "")
                            if msg_type == "stream_event":
                                event_payload = data.get("event", {})
                                delta = {}
                                if isinstance(event_payload, dict):
                                    delta = event_payload.get("delta", {}) if isinstance(event_payload.get("delta"), dict) else {}
                                if not delta and isinstance(data.get("delta"), dict):
                                    delta = data.get("delta", {})
                                text = None
                                if isinstance(delta, dict):
                                    text = delta.get("text") or delta.get("content")
                                if not text and isinstance(event_payload, dict):
                                    text = event_payload.get("text") or event_payload.get("content")
                                if not text:
                                    text = data.get("text")
                                if isinstance(text, str) and text:
                                    filtered_text = _filter_agent_message(text)
                                    if not filtered_text:
                                        continue
                                    indicator_chunk = _build_long_operation_chunk(
                                        _long_operation_indicator(filtered_text),
                                        request_id,
                                        model,
                                        long_ops_seen,
                                    )
                                    if indicator_chunk:
                                        yield indicator_chunk
                                    content_streamed = True
                                    output_parts.append(filtered_text)
                                    if debug_emitter:
                                        await debug_emitter.emit(
                                            DebugEventType.RESPONSE_CHUNK,
                                            "AGENT",
                                            filtered_text[:200],
                                        )
                                    yield ChatCompletionChunk(
                                        id=request_id,
                                        model=model,
                                        choices=[
                                            ChunkChoice(delta=Delta(content=filtered_text))
                                        ],
                                    )
                            elif msg_type == "result":
                                result_text = data.get("result") or data.get("text")
                                if isinstance(result_text, str) and result_text:
                                    filtered_text = _filter_agent_message(result_text)
                                    if not filtered_text:
                                        continue
                                    text_to_emit = (
                                        _dedupe_result_text(filtered_text, output_parts)
                                        if content_streamed
                                        else filtered_text
                                    )
                                    if text_to_emit:
                                        content_streamed = True
                                        output_parts.append(text_to_emit)
                                        if debug_emitter:
                                            await debug_emitter.emit(
                                                DebugEventType.RESPONSE_CHUNK,
                                                "AGENT",
                                                text_to_emit[:200],
                                            )
                                        yield ChatCompletionChunk(
                                            id=request_id,
                                            model=model,
                                            choices=[
                                                ChunkChoice(delta=Delta(content=text_to_emit))
                                            ],
                                        )
                            elif msg_type == "assistant":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict):
                                            if block.get("type") == "text":
                                                text = block.get("text", "")
                                                if text:
                                                    filtered_text = _filter_agent_message(text)
                                                    if not filtered_text:
                                                        continue
                                                    indicator_chunk = _build_long_operation_chunk(
                                                        _long_operation_indicator(filtered_text),
                                                        request_id,
                                                        model,
                                                        long_ops_seen,
                                                    )
                                                    if indicator_chunk:
                                                        yield indicator_chunk
                                                    text_to_emit = (
                                                        _dedupe_result_text(filtered_text, output_parts)
                                                        if content_streamed
                                                        else filtered_text
                                                    )
                                                    if text_to_emit:
                                                        # Stream text content immediately so it appears in chat
                                                        content_streamed = True
                                                        output_parts.append(text_to_emit)
                                                        if debug_emitter:
                                                            await debug_emitter.emit(
                                                                DebugEventType.RESPONSE_CHUNK,
                                                                "AGENT",
                                                                text_to_emit[:200],
                                                            )
                                                        yield ChatCompletionChunk(
                                                            id=request_id,
                                                            model=model,
                                                            choices=[
                                                                ChunkChoice(
                                                                    delta=Delta(content=text_to_emit)
                                                                )
                                                            ],
                                                        )
                                            elif block.get("type") == "tool_use":
                                                tool_name = block.get("name", "")
                                                tool_input = block.get("input", {})
                                                # Extract useful info from tool input
                                                tool_detail = ""
                                                cmd = ""
                                                if tool_name == "Bash":
                                                    cmd = tool_input.get("command", "")[:100]
                                                    if cmd:
                                                        tool_detail = f": {cmd}"
                                                elif tool_name in ("Read", "Write", "Edit", "Glob", "Grep"):
                                                    path = tool_input.get("file_path", "") or tool_input.get("path", "") or tool_input.get("pattern", "")
                                                    if path:
                                                        tool_detail = f": {path[:80]}"
                                                indicator_chunk = _build_long_operation_chunk(
                                                    _long_operation_indicator(cmd),
                                                    request_id,
                                                    model,
                                                    long_ops_seen,
                                                )
                                                if indicator_chunk:
                                                    yield indicator_chunk
                                                if debug_emitter:
                                                    await debug_emitter.emit(
                                                        DebugEventType.TOOL_CALL_START,
                                                        _debug_step_for_tool(tool_name),
                                                        f"Using tool: {tool_name}{tool_detail}",
                                                        data={"tool": tool_name},
                                                    )
                                                yield ChatCompletionChunk(
                                                    id=request_id,
                                                    model=model,
                                                    choices=[
                                                        ChunkChoice(
                                                            delta=Delta(
                                                                reasoning_content=f"Using tool: {tool_name}{tool_detail}\n"
                                                            )
                                                        )
                                                    ],
                                                )
                                            elif block.get("type") == "thinking":
                                                # Extended thinking content
                                                thinking_text = block.get("thinking", "")
                                                if thinking_text:
                                                    yield ChatCompletionChunk(
                                                        id=request_id,
                                                        model=model,
                                                        choices=[
                                                            ChunkChoice(
                                                                delta=Delta(
                                                                    reasoning_content=thinking_text
                                                                )
                                                            )
                                                        ],
                                                    )
                            elif msg_type == "user":
                                # Tool result - stream useful output
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "tool_result":
                                            tool_content = block.get("content", "")
                                            if isinstance(tool_content, str) and tool_content.strip():
                                                tool_result_path = _extract_tool_result_path(tool_content)
                                                if tool_result_path and tool_result_path not in seen_tool_results:
                                                    seen_tool_results.add(tool_result_path)
                                                    recovered_text = await self._read_tool_result_text(
                                                        client, sandbox_id, tool_result_path
                                                    )
                                                    if recovered_text:
                                                        recovered_text = await self._materialize_data_url_images(
                                                            client, sandbox_id, recovered_text
                                                        )
                                                        recovered_text = process_agent_response(
                                                            recovered_text, sandbox_url
                                                        )
                                                        recovered_output_parts.append(recovered_text)
                                                # Truncate very long outputs
                                                truncated = tool_content[:500]
                                                if len(tool_content) > 500:
                                                    truncated += "... (truncated)"
                                                yield ChatCompletionChunk(
                                                    id=request_id,
                                                    model=model,
                                                    choices=[
                                                        ChunkChoice(
                                                            delta=Delta(
                                                                reasoning_content=f"Tool output:\n{truncated}\n"
                                                            )
                                                        )
                                                    ],
                                                )
                            elif msg_type == "system":
                                # System messages - often contain warnings or status
                                message = data.get("message", "")
                                if isinstance(message, str):
                                    filtered_message = _filter_agent_message(message)
                                else:
                                    filtered_message = None
                                if filtered_message:
                                    yield ChatCompletionChunk(
                                        id=request_id,
                                        model=model,
                                        choices=[
                                            ChunkChoice(
                                                delta=Delta(
                                                    reasoning_content=f"{filtered_message}\n"
                                                )
                                            )
                                        ],
                                    )

                    elif event_type == "stream_event":
                        event_payload = event.get("event", {})
                        delta = {}
                        if isinstance(event_payload, dict):
                            delta = event_payload.get("delta", {}) if isinstance(event_payload.get("delta"), dict) else {}
                        if not delta and isinstance(event.get("delta"), dict):
                            delta = event.get("delta", {})
                        text = None
                        if isinstance(delta, dict):
                            text = delta.get("text") or delta.get("content")
                        if not text and isinstance(event_payload, dict):
                            text = event_payload.get("text") or event_payload.get("content")
                        if not text:
                            text = event.get("text")
                        if isinstance(text, str) and text:
                            filtered_text = _filter_agent_message(text)
                            if not filtered_text:
                                continue
                            indicator_chunk = _build_long_operation_chunk(
                                _long_operation_indicator(filtered_text),
                                request_id,
                                model,
                                long_ops_seen,
                            )
                            if indicator_chunk:
                                yield indicator_chunk
                            content_streamed = True
                            output_parts.append(filtered_text)
                            if debug_emitter:
                                await debug_emitter.emit(
                                    DebugEventType.RESPONSE_CHUNK,
                                    "AGENT",
                                    filtered_text[:200],
                                )
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(delta=Delta(content=filtered_text))
                                ],
                            )

                    elif event_type == "result":
                        result_text = event.get("result") or event.get("text")
                        if isinstance(result_text, str) and result_text:
                            filtered_text = _filter_agent_message(result_text)
                            if not filtered_text:
                                continue
                            text_to_emit = (
                                _dedupe_result_text(filtered_text, output_parts)
                                if content_streamed
                                else filtered_text
                            )
                            if text_to_emit:
                                content_streamed = True
                                output_parts.append(text_to_emit)
                                if debug_emitter:
                                    await debug_emitter.emit(
                                        DebugEventType.RESPONSE_CHUNK,
                                        "AGENT",
                                        text_to_emit[:200],
                                    )
                                yield ChatCompletionChunk(
                                    id=request_id,
                                    model=model,
                                    choices=[
                                        ChunkChoice(delta=Delta(content=text_to_emit))
                                    ],
                                )

                    elif event_type == "files-update":
                        # File changes detected
                        changes = event.get("changes", [])
                        if changes:
                            if debug_emitter:
                                for change in changes:
                                    filename = change.get("path", "unknown")
                                    change_type = change.get("changeType", "modified")
                                    await debug_emitter.emit(
                                        DebugEventType.FILE_CREATED
                                        if change_type == "created"
                                        else DebugEventType.FILE_MODIFIED,
                                        "TOOL_FILES",
                                        f"File {change_type}: {filename}",
                                        data={
                                            "filename": filename,
                                            "change_type": change_type,
                                        },
                                    )
                            change_summary = ", ".join(
                                f"{c.get('path', 'unknown')} ({c.get('changeType', 'modified')})"
                                for c in changes[:5]
                            )
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(
                                            reasoning_content=f"Files changed: {change_summary}\n"
                                        )
                                    )
                                ],
                            )

                    elif event_type == "heartbeat":
                        # Keep-alive - send progress indicator if no content yet
                        elapsed = event.get("elapsed", 0)
                        if not content_streamed and elapsed > 10:
                            # Show progress every 15 seconds when no output yet
                            elapsed_int = int(elapsed)
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(
                                            reasoning_content=f"⏳ Agent working... ({elapsed_int}s)\n"
                                        )
                                    )
                                ],
                            )

                    elif event_type == "retry":
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[
                                ChunkChoice(
                                    delta=Delta(
                                        reasoning_content=(
                                            "Operation taking longer than expected, retrying...\n"
                                        )
                                    )
                                )
                            ],
                        )

                    elif event_type == "complete":
                        # Agent execution complete
                        exit_code = event.get("exitCode", 0)
                        success = event.get("success", exit_code == 0)
                        duration = event.get("duration", 0)
                        if debug_emitter:
                            await debug_emitter.emit(
                                DebugEventType.RESPONSE_COMPLETE,
                                "SSE",
                                f"Agent completed ({'success' if success else 'failed'})",
                                data={
                                    "success": success,
                                    "exit_code": exit_code,
                                    "duration": duration,
                                },
                            )
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[
                                ChunkChoice(
                                    delta=Delta(
                                        reasoning_content=(
                                            f"Agent completed ({'success' if success else 'failed'}) "
                                            f"in {duration:.1f}s\n"
                                        )
                                    )
                                )
                            ],
                        )

                    elif event_type == "error":
                        # Error from agent
                        error_msg = _format_agent_error(
                            str(event.get("error", "Unknown error"))
                        )
                        has_error = True
                        output_parts.append(f"Error: {error_msg}")
                        if debug_emitter:
                            await debug_emitter.emit(
                                DebugEventType.ERROR,
                                "AGENT",
                                f"Error: {error_msg}",
                            )
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[
                                ChunkChoice(
                                    delta=Delta(
                                        reasoning_content=f"Error: {error_msg}\n"
                                    )
                                )
                            ],
                        )

                # Only emit final content if we haven't streamed any content yet
                # (content was already streamed from agent-output events)
                if not content_streamed:
                    if output_parts:
                        result = "\n".join(output_parts)
                    elif recovered_output_parts:
                        result = "\n".join(recovered_output_parts)
                    else:
                        result = "Agent completed without output."
                    # Clean up Aider-specific output formatting
                    result = _clean_aider_output(result)
                    result = process_agent_response(result, sandbox_url)
                    if result:  # Only emit if there's content after cleaning
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[ChunkChoice(delta=Delta(content=result))],
                        )

                # Collect artifacts
                artifacts = await self._collect_artifacts(client, sandbox_id, public_url)
                artifacts_present = bool(artifacts)
                if artifacts:
                    artifact_payload = [artifact.model_dump(mode="json") for artifact in artifacts]
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    janus={
                                        "event": "artifacts",
                                        "payload": {"items": artifact_payload},
                                    }
                                )
                            )
                        ],
                    )
                    links = self._format_artifact_links(artifacts)
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    content=f"\n\nArtifacts available:\n{links}"
                                )
                            )
                        ],
                    )

            finally:
                grace_seconds = (
                    self._artifact_grace_seconds if artifacts_present else 0
                )
                if grace_seconds > 0:
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    reasoning_content=(
                                        "Keeping sandbox alive for artifact downloads "
                                        f"({grace_seconds}s)...\n"
                                    )
                                )
                            )
                        ],
                    )
                    self._schedule_sandbox_termination(sandbox_id, grace_seconds)
                else:
                    # Cleanup immediately
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(reasoning_content="Terminating sandbox...\n")
                            )
                        ],
                    )
                    await self._terminate_sandbox(client, sandbox_id)

                sandbox_seconds = time.perf_counter() - sandbox_start

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                    ],
                )

                # Include usage with sandbox time
                if request.stream_options and request.stream_options.include_usage:
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[],
                        usage=Usage(
                            prompt_tokens=0,
                            completion_tokens=0,
                            total_tokens=0,
                            sandbox_seconds=sandbox_seconds,
                        ),
                    )

    async def execute_via_agent_api_in_sandbox(
        self,
        sandbox_id: str,
        public_url: str | None,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
        baseline_agent_override: str | None = None,
        run_state: dict[str, Any] | None = None,
        terminate_on_finish: bool = False,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Execute a task in a warmed sandbox using Sandy's agent/run API."""
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)
        has_images = contains_images(request.messages)

        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.SANDBOX_INIT,
                "SANDY",
                "Starting warm sandbox execution",
                data={"warm_pool": True, "sandbox_id": sandbox_id},
            )

        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
        )

        if not self.is_available:
            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.ERROR,
                    "SANDY",
                    "Sandy is not configured",
                )
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[
                    ChunkChoice(
                        delta=Delta(
                            content=(
                                "I would execute this task in a Sandy sandbox:\n\n"
                                f"**Task:** {task}\n\nSandy is not currently configured. "
                                "Please configure SANDY_BASE_URL to enable sandbox execution."
                            )
                        )
                    )
                ],
            )
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)],
            )
            return

        agent = self._select_agent_for_api(baseline_agent_override)
        api_model = self._select_model_for_api(request, agent=agent)

        start_message = (
            "Starting claude-code agent with intelligent model routing among Chutes models"
            if agent in {"claude", "claude-code"}
            else f"Starting {agent} agent in Sandy sandbox"
        )
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.AGENT_THINKING,
                "AGENT",
                f"{start_message} (warm sandbox)",
                data={"agent": agent, "model": api_model, "sandbox_id": sandbox_id},
            )

        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[
                ChunkChoice(
                    delta=Delta(reasoning_content=f"{start_message} (warm)...\n")
                )
            ],
        )

        sandbox_start = time.perf_counter()
        output_parts: list[str] = []
        recovered_output_parts: list[str] = []
        seen_tool_results: set[str] = set()
        long_ops_seen: set[str] = set()
        content_streamed = False
        has_error = False
        exit_code = 0
        artifacts_present = False
        termination_scheduled = False

        async with self._client_factory() as client:
            sandbox_url = self._sandbox_url(sandbox_id, public_url)
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[
                    ChunkChoice(
                        delta=Delta(
                            reasoning_content=f"Using warm sandbox: {sandbox_id}\n"
                        )
                    )
                ],
            )

            try:
                if not self._system_prompt_path.exists():
                    logger.warning(
                        "system_prompt_missing", path=str(self._system_prompt_path)
                    )

                async for event in self._run_agent_via_api_with_retry(
                    client,
                    sandbox_id,
                    agent,
                    api_model,
                    task,
                    request=request,
                    public_url=public_url,
                    has_images=has_images,
                    max_duration=self._timeout,
                    max_retries=2,
                ):
                    event_type = event.get("type", "")

                    if event_type == "status":
                        message = event.get("message", "")
                        filtered_message = _filter_agent_message(message) if message else None
                        if filtered_message:
                            indicator_chunk = _build_long_operation_chunk(
                                _long_operation_indicator(filtered_message),
                                request_id,
                                model,
                                long_ops_seen,
                            )
                            if indicator_chunk:
                                yield indicator_chunk
                            if debug_emitter:
                                await debug_emitter.emit(
                                    DebugEventType.AGENT_THINKING,
                                    "AGENT",
                                    filtered_message,
                                )
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(reasoning_content=f"{filtered_message}\n")
                                    )
                                ],
                            )

                    elif event_type == "output":
                        text = _strip_ansi(event.get("text", ""))
                        filtered_text = _filter_agent_message(text) if text else None
                        if filtered_text:
                            indicator_chunk = _build_long_operation_chunk(
                                _long_operation_indicator(filtered_text),
                                request_id,
                                model,
                                long_ops_seen,
                            )
                            if indicator_chunk:
                                yield indicator_chunk
                            tool_result_path = _extract_tool_result_path(filtered_text)
                            if tool_result_path and tool_result_path not in seen_tool_results:
                                seen_tool_results.add(tool_result_path)
                                recovered_text = await self._read_tool_result_text(
                                    client, sandbox_id, tool_result_path
                                )
                                if recovered_text:
                                    recovered_text = await self._materialize_data_url_images(
                                        client, sandbox_id, recovered_text
                                    )
                                    recovered_text = process_agent_response(
                                        recovered_text, sandbox_url
                                    )
                                    recovered_output_parts.append(recovered_text)
                            if debug_emitter:
                                await debug_emitter.emit(
                                    DebugEventType.RESPONSE_CHUNK,
                                    "AGENT",
                                    filtered_text,
                                )
                            output_parts.append(filtered_text)
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(reasoning_content=f"{filtered_text}\n")
                                    )
                                ],
                            )

                    elif event_type == "agent-output":
                        data = event.get("data", {})
                        if isinstance(data, dict):
                            msg_type = data.get("type", "")
                            if msg_type == "stream_event":
                                event_payload = data.get("event", {})
                                delta = {}
                                if isinstance(event_payload, dict):
                                    delta = event_payload.get("delta", {}) if isinstance(event_payload.get("delta"), dict) else {}
                                if not delta and isinstance(data.get("delta"), dict):
                                    delta = data.get("delta", {})
                                text = None
                                if isinstance(delta, dict):
                                    text = delta.get("text") or delta.get("content")
                                if not text and isinstance(event_payload, dict):
                                    text = event_payload.get("text") or event_payload.get("content")
                                if not text:
                                    text = data.get("text")
                                if isinstance(text, str) and text:
                                    filtered_text = _filter_agent_message(text)
                                    if not filtered_text:
                                        continue
                                    content_streamed = True
                                    output_parts.append(filtered_text)
                                    if debug_emitter:
                                        await debug_emitter.emit(
                                            DebugEventType.RESPONSE_CHUNK,
                                            "AGENT",
                                            filtered_text[:200],
                                        )
                                    yield ChatCompletionChunk(
                                        id=request_id,
                                        model=model,
                                        choices=[
                                            ChunkChoice(delta=Delta(content=filtered_text))
                                        ],
                                    )
                            elif msg_type == "result":
                                result_text = data.get("result") or data.get("text")
                                if isinstance(result_text, str) and result_text:
                                    filtered_text = _filter_agent_message(result_text)
                                    if not filtered_text:
                                        continue
                                    text_to_emit = (
                                        _dedupe_result_text(filtered_text, output_parts)
                                        if content_streamed
                                        else filtered_text
                                    )
                                    if text_to_emit:
                                        content_streamed = True
                                        output_parts.append(text_to_emit)
                                        if debug_emitter:
                                            await debug_emitter.emit(
                                                DebugEventType.RESPONSE_CHUNK,
                                                "AGENT",
                                                text_to_emit[:200],
                                            )
                                        yield ChatCompletionChunk(
                                            id=request_id,
                                            model=model,
                                            choices=[
                                                ChunkChoice(delta=Delta(content=text_to_emit))
                                            ],
                                        )
                            elif msg_type == "assistant":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text = block.get("text", "")
                                            if text:
                                                filtered_text = _filter_agent_message(text)
                                                if filtered_text:
                                                    output_parts.append(filtered_text)
                            elif msg_type == "user":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "tool_result":
                                            tool_content = block.get("content", "")
                                            if isinstance(tool_content, str) and tool_content.strip():
                                                tool_result_path = _extract_tool_result_path(tool_content)
                                                if tool_result_path and tool_result_path not in seen_tool_results:
                                                    seen_tool_results.add(tool_result_path)
                                                    recovered_text = await self._read_tool_result_text(
                                                        client, sandbox_id, tool_result_path
                                                    )
                                                    if recovered_text:
                                                        recovered_text = await self._materialize_data_url_images(
                                                            client, sandbox_id, recovered_text
                                                        )
                                                        recovered_text = process_agent_response(
                                                            recovered_text, sandbox_url
                                                        )
                                                        recovered_output_parts.append(recovered_text)
                                                truncated = tool_content[:500]
                                                if len(tool_content) > 500:
                                                    truncated += "... (truncated)"
                                                yield ChatCompletionChunk(
                                                    id=request_id,
                                                    model=model,
                                                    choices=[
                                                        ChunkChoice(
                                                            delta=Delta(
                                                                reasoning_content=f"Tool output:\n{truncated}\n"
                                                            )
                                                        )
                                                    ],
                                                )

                    elif event_type == "stream_event":
                        event_payload = event.get("event", {})
                        delta = {}
                        if isinstance(event_payload, dict):
                            delta = event_payload.get("delta", {}) if isinstance(event_payload.get("delta"), dict) else {}
                        if not delta and isinstance(event.get("delta"), dict):
                            delta = event.get("delta", {})
                        text = None
                        if isinstance(delta, dict):
                            text = delta.get("text") or delta.get("content")
                        if not text and isinstance(event_payload, dict):
                            text = event_payload.get("text") or event_payload.get("content")
                        if not text:
                            text = event.get("text")
                        if isinstance(text, str) and text:
                            filtered_text = _filter_agent_message(text)
                            if not filtered_text:
                                continue
                            indicator_chunk = _build_long_operation_chunk(
                                _long_operation_indicator(filtered_text),
                                request_id,
                                model,
                                long_ops_seen,
                            )
                            if indicator_chunk:
                                yield indicator_chunk
                            content_streamed = True
                            output_parts.append(filtered_text)
                            if debug_emitter:
                                await debug_emitter.emit(
                                    DebugEventType.RESPONSE_CHUNK,
                                    "AGENT",
                                    filtered_text[:200],
                                )
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(delta=Delta(content=filtered_text))
                                ],
                            )

                    elif event_type == "result":
                        result_text = event.get("result") or event.get("text")
                        if isinstance(result_text, str) and result_text:
                            filtered_text = _filter_agent_message(result_text)
                            if not filtered_text:
                                continue
                            text_to_emit = (
                                _dedupe_result_text(filtered_text, output_parts)
                                if content_streamed
                                else filtered_text
                            )
                            if text_to_emit:
                                content_streamed = True
                                output_parts.append(text_to_emit)
                                if debug_emitter:
                                    await debug_emitter.emit(
                                        DebugEventType.RESPONSE_CHUNK,
                                        "AGENT",
                                        text_to_emit[:200],
                                    )
                                yield ChatCompletionChunk(
                                    id=request_id,
                                    model=model,
                                    choices=[
                                        ChunkChoice(delta=Delta(content=text_to_emit))
                                    ],
                                )

                    elif event_type == "files-update":
                        changes = event.get("changes", [])
                        if changes:
                            if debug_emitter:
                                for change in changes:
                                    filename = change.get("path", "unknown")
                                    change_type = change.get("changeType", "modified")
                                    await debug_emitter.emit(
                                        DebugEventType.FILE_CREATED
                                        if change_type == "created"
                                        else DebugEventType.FILE_MODIFIED,
                                        "TOOL_FILES",
                                        f"File {change_type}: {filename}",
                                        data={
                                            "filename": filename,
                                            "change_type": change_type,
                                        },
                                    )
                            change_summary = ", ".join(
                                f"{c.get('path', 'unknown')} ({c.get('changeType', 'modified')})"
                                for c in changes[:5]
                            )
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(
                                            reasoning_content=f"Files changed: {change_summary}\n"
                                        )
                                    )
                                ],
                            )

                    elif event_type == "heartbeat":
                        elapsed = event.get("elapsed", 0)
                        if not content_streamed and elapsed > 10:
                            elapsed_int = int(elapsed)
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(
                                            reasoning_content=f"⏳ Agent working... ({elapsed_int}s)\n"
                                        )
                                    )
                                ],
                            )

                    elif event_type == "retry":
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[
                                ChunkChoice(
                                    delta=Delta(
                                        reasoning_content=(
                                            "Operation taking longer than expected, retrying...\n"
                                        )
                                    )
                                )
                            ],
                        )

                    elif event_type == "complete":
                        exit_code = event.get("exitCode", 0)
                        success = event.get("success", exit_code == 0)
                        duration = event.get("duration", 0)
                        if debug_emitter:
                            await debug_emitter.emit(
                                DebugEventType.RESPONSE_COMPLETE,
                                "SSE",
                                f"Agent completed ({'success' if success else 'failed'})",
                                data={
                                    "success": success,
                                    "exit_code": exit_code,
                                    "duration": duration,
                                },
                            )
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[
                                ChunkChoice(
                                    delta=Delta(
                                        reasoning_content=(
                                            f"Agent completed ({'success' if success else 'failed'}) "
                                            f"in {duration:.1f}s\n"
                                        )
                                    )
                                )
                            ],
                        )

                    elif event_type == "error":
                        error_msg = _format_agent_error(
                            str(event.get("error", "Unknown error"))
                        )
                        has_error = True
                        output_parts.append(f"Error: {error_msg}")
                        if debug_emitter:
                            await debug_emitter.emit(
                                DebugEventType.ERROR,
                                "AGENT",
                                f"Error: {error_msg}",
                            )
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[
                                ChunkChoice(
                                    delta=Delta(
                                        reasoning_content=f"Error: {error_msg}\n"
                                    )
                                )
                            ],
                        )

                if not content_streamed:
                    if output_parts:
                        result = "\n".join(output_parts)
                    elif recovered_output_parts:
                        result = "\n".join(recovered_output_parts)
                    else:
                        result = "Agent completed without output."
                    result = _clean_aider_output(result)
                    result = process_agent_response(result, sandbox_url)
                    if result:
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[ChunkChoice(delta=Delta(content=result))],
                        )

                artifacts = await self._collect_artifacts(client, sandbox_id, public_url)
                artifacts_present = bool(artifacts)
                if artifacts:
                    artifact_payload = [artifact.model_dump(mode="json") for artifact in artifacts]
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    janus={
                                        "event": "artifacts",
                                        "payload": {"items": artifact_payload},
                                    }
                                )
                            )
                        ],
                    )
                    links = self._format_artifact_links(artifacts)
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    content=f"\n\nArtifacts available:\n{links}"
                                )
                            )
                        ],
                    )

            finally:
                if artifacts_present and self._artifact_grace_seconds > 0:
                    grace_seconds = self._artifact_grace_seconds
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(
                                    reasoning_content=(
                                        "Keeping sandbox alive for artifact downloads "
                                        f"({grace_seconds}s)...\n"
                                    )
                                )
                            )
                        ],
                    )
                    self._schedule_sandbox_termination(sandbox_id, grace_seconds)
                    termination_scheduled = True
                elif terminate_on_finish or has_error:
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(reasoning_content="Terminating sandbox...\n")
                            )
                        ],
                    )
                    await self._terminate_sandbox(client, sandbox_id)

                sandbox_seconds = time.perf_counter() - sandbox_start

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)
                    ],
                )

                if request.stream_options and request.stream_options.include_usage:
                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[],
                        usage=Usage(
                            prompt_tokens=0,
                            completion_tokens=0,
                            total_tokens=0,
                            sandbox_seconds=sandbox_seconds,
                        ),
                    )

                if run_state is not None:
                    run_state.update(
                        {
                            "has_error": has_error,
                            "exit_code": exit_code,
                            "artifacts_present": artifacts_present,
                            "termination_scheduled": termination_scheduled,
                        }
                    )


@lru_cache
def get_sandy_service() -> SandyService:
    """Get cached Sandy service instance."""
    return SandyService(get_settings())
