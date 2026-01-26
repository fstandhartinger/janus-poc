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

logger = structlog.get_logger()


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
    # Include common pip --user install paths and standard paths
    # Note: Using actual paths instead of unexpanded shell variables
    _default_path = (
        "/root/.local/bin:"  # pip --user for root
        "/usr/local/bin:"  # system-wide pip installs
        "/agent-pack/bin:"  # agent pack binaries
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
        self._timeout = settings.sandy_timeout
        self._client_factory = client_factory or httpx.AsyncClient
        self._baseline_root = Path(__file__).resolve().parents[2]
        self._agent_pack_path = self._resolve_path(settings.agent_pack_path)
        self._system_prompt_path = self._resolve_path(settings.system_prompt_path)
        self._artifact_port = settings.artifact_port
        self._artifact_dir = settings.artifact_dir
        self._artifact_ttl = settings.artifact_ttl_seconds
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

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the baseline root if needed."""
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return (self._baseline_root / candidate).resolve()

    def _agent_pack_dest_root(self) -> str:
        """Get the agent pack destination path inside the sandbox."""
        return "/agent-pack"

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
            "JANUS_SYSTEM_PROMPT_PATH": "/agent-pack/prompts/system.md",
            "JANUS_ENABLE_WEB_SEARCH": str(self._settings.enable_web_search).lower(),
            "JANUS_ENABLE_CODE_EXECUTION": str(self._settings.enable_code_execution).lower(),
            "JANUS_ENABLE_FILE_TOOLS": str(self._settings.enable_file_tools).lower(),
            "JANUS_ENABLE_NETWORK": "true",
            "CHUTES_API_KEY": chutes_api_key,
            "CHUTES_API_URL": chutes_api_url,
            "CHUTES_API_BASE": chutes_api_url,
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
            "PATH": self._default_path,
        }
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
        return env

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
        elif agent == "claude" or agent == "claude-code":
            # Claude Code CLI agent
            # -p: Print mode (non-interactive)
            # --verbose: REQUIRED with stream-json for real-time progress events
            # --output-format stream-json: Structured JSONL output
            # --no-session-persistence: Fresh context each run (no session contamination)
            # --dangerously-skip-permissions: YOLO mode for automation
            # IMPORTANT: Must run from /workspace where CLAUDE.md is located!
            # Claude Code automatically reads CLAUDE.md from cwd for project context.
            # Use bash -c to properly handle cd + command chain.
            claude_cmd = (
                f"cd /workspace && claude -p --verbose --output-format stream-json "
                f"--no-session-persistence --dangerously-skip-permissions "
                f"--allowedTools Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch "
                f"{quoted_task}"
            )
            command = ["bash", "-c", shlex.quote(claude_cmd)]
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
                "--non-interactive",
                "--context", system_prompt_path,
                quoted_task,
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
        logger.info(
            "agent_command_built",
            agent=agent,
            command_preview=full_command[:1000],
            full_command_length=len(full_command),
        )
        return full_command

    def _agent_candidates(self) -> list[str]:
        """Determine preferred agent order.

        Supported agents:
        - claude / claude-code: Anthropic's Claude Code CLI
        - aider: AI pair programmer
        - opencode: Factory OpenCode agent
        - openhands: OpenHands CLI
        - builtin: Simple template-based fallback
        """
        requested = self._baseline_agent.strip().lower()
        logger.info(
            "agent_candidates_config",
            requested_agent=requested,
            baseline_agent_setting=self._baseline_agent,
        )
        if requested in {"builtin", "run_agent"}:
            return ["builtin"]
        if requested in {"claude", "claude-code"}:
            return ["claude", "aider", "builtin"]
        if requested:
            return [requested, "claude", "aider", "builtin"]
        # Default order: prefer Claude Code, then aider, then others
        return ["claude", "aider", "opencode", "openhands", "builtin"]

    async def _select_agent(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
    ) -> str:
        """Pick an available CLI agent inside the sandbox."""
        candidates = self._agent_candidates()
        logger.info(
            "agent_selection_start",
            candidates=candidates,
            baseline_agent_config=self._baseline_agent,
            path=self._default_path,
        )

        # First, log what's available in the PATH for debugging
        path_check_cmd = f"PATH={shlex.quote(self._default_path)} ls -la /root/.local/bin/ 2>/dev/null || echo 'No /root/.local/bin'; which aider claude opencode openhands 2>/dev/null || echo 'None found in PATH'"
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

            # Handle claude-code alias
            binary_name = "claude" if candidate in {"claude", "claude-code"} else candidate

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
            payload = {
                "path": dest_path,
                "content": base64.b64encode(content).decode("utf-8"),
                "encoding": "base64",
            }
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

    async def _run_agent_via_api(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
        agent: str,
        model: str,
        prompt: str,
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

        # Pass the public router URL if configured - enables smart model switching,
        # 429 fallbacks, and multimodal routing for Sandy agents
        if self._settings.public_router_url:
            payload["apiBaseUrl"] = self._settings.public_router_url

        logger.info(
            "agent_api_request",
            sandbox_id=sandbox_id,
            agent=agent,
            model=model,
            prompt_length=len(prompt),
            max_duration=max_duration,
            router_url=self._settings.public_router_url,
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
                    read=float(max_duration + 60),  # Extra buffer for response
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
        requested = (requested_agent or self._baseline_agent).strip().lower()
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

    def _select_model_for_api(self, request: ChatCompletionRequest) -> str:
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

                selected_agent = await self._select_agent(client, sandbox_id)
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
                await self._terminate_sandbox(client, sandbox_id)

    async def execute_complex(
        self,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
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

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(reasoning_content="Selecting CLI agent...\n")
                        )
                    ],
                )

                selected_agent = await self._select_agent(client, sandbox_id)
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
                if artifacts:
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
                # Cleanup
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
        api_model = self._select_model_for_api(request)
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.AGENT_THINKING,
                "AGENT",
                f"Starting {agent} agent with model {api_model}",
                data={"agent": agent, "model": api_model},
            )
        sandbox_start = time.perf_counter()
        output_parts: list[str] = []

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
                async for event in self._run_agent_via_api(
                    client,
                    sandbox_id,
                    agent,
                    api_model,
                    task,
                    max_duration=self._timeout,
                ):
                    event_type = event.get("type", "")

                    if event_type == "output":
                        text = _strip_ansi(event.get("text", ""))
                        if text:
                            output_parts.append(text)

                    elif event_type == "agent-output":
                        data = event.get("data", {})
                        if isinstance(data, dict):
                            msg_type = data.get("type", "")
                            if msg_type == "assistant":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text = block.get("text", "")
                                            if text:
                                                output_parts.append(text)

                    elif event_type == "error":
                        error_msg = event.get("error", "Unknown error")
                        output_parts.append(f"Error: {error_msg}")

                result = "\n".join(output_parts) if output_parts else "Agent completed without output."
                # Clean up Aider-specific output formatting
                result = _clean_aider_output(result)
                result = process_agent_response(result, sandbox_url)

                artifacts = await self._collect_artifacts(client, sandbox_id, public_url)
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
                await self._terminate_sandbox(client, sandbox_id)

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
        - Provides faster sandbox boot times (no bootstrap needed)
        - Streams real-time output from the agent
        """
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)

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
        api_model = self._select_model_for_api(request)

        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.AGENT_THINKING,
                "AGENT",
                f"Starting {agent} agent with model {api_model}",
                data={"agent": agent, "model": api_model},
            )

        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[
                ChunkChoice(
                    delta=Delta(
                        reasoning_content=f"Starting {agent} agent with model {api_model}...\n"
                    )
                )
            ],
        )

        sandbox_start = time.perf_counter()
        output_parts: list[str] = []
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
                # Run agent via Sandy's API
                async for event in self._run_agent_via_api(
                    client,
                    sandbox_id,
                    agent,
                    api_model,
                    task,
                    max_duration=self._timeout,
                ):
                    event_type = event.get("type", "")

                    if event_type == "status":
                        # Progress status messages
                        message = event.get("message", "")
                        if message:
                            if debug_emitter:
                                await debug_emitter.emit(
                                    DebugEventType.AGENT_THINKING,
                                    "AGENT",
                                    message,
                                )
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(reasoning_content=f"{message}\n")
                                    )
                                ],
                            )

                    elif event_type == "output":
                        # Text output from agent
                        text = _strip_ansi(event.get("text", ""))
                        if text:
                            if debug_emitter:
                                await debug_emitter.emit(
                                    DebugEventType.RESPONSE_CHUNK,
                                    "AGENT",
                                    text,
                                )
                            output_parts.append(text)
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(reasoning_content=f"{text}\n")
                                    )
                                ],
                            )

                    elif event_type == "agent-output":
                        # Structured agent output (especially from claude-code)
                        data = event.get("data", {})
                        if isinstance(data, dict):
                            # Extract content from Claude Code stream-json output
                            msg_type = data.get("type", "")
                            if msg_type == "assistant":
                                message = data.get("message", {})
                                content = message.get("content", [])
                                if isinstance(content, list):
                                    for block in content:
                                        if isinstance(block, dict):
                                            if block.get("type") == "text":
                                                text = block.get("text", "")
                                                if text:
                                                    # Stream text content immediately so it appears in chat
                                                    content_streamed = True
                                                    if debug_emitter:
                                                        await debug_emitter.emit(
                                                            DebugEventType.RESPONSE_CHUNK,
                                                            "AGENT",
                                                            text[:200],
                                                        )
                                                    yield ChatCompletionChunk(
                                                        id=request_id,
                                                        model=model,
                                                        choices=[
                                                            ChunkChoice(
                                                                delta=Delta(content=text)
                                                            )
                                                        ],
                                                    )
                                            elif block.get("type") == "tool_use":
                                                tool_name = block.get("name", "")
                                                tool_input = block.get("input", {})
                                                # Extract useful info from tool input
                                                tool_detail = ""
                                                if tool_name == "Bash":
                                                    cmd = tool_input.get("command", "")[:100]
                                                    if cmd:
                                                        tool_detail = f": {cmd}"
                                                elif tool_name in ("Read", "Write", "Edit", "Glob", "Grep"):
                                                    path = tool_input.get("file_path", "") or tool_input.get("path", "") or tool_input.get("pattern", "")
                                                    if path:
                                                        tool_detail = f": {path[:80]}"
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
                                if isinstance(message, str) and message.strip():
                                    yield ChatCompletionChunk(
                                        id=request_id,
                                        model=model,
                                        choices=[
                                            ChunkChoice(
                                                delta=Delta(
                                                    reasoning_content=f"{message}\n"
                                                )
                                            )
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
                        error_msg = event.get("error", "Unknown error")
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
                    result = "\n".join(output_parts) if output_parts else "Agent completed without output."
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
                if artifacts:
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
                # Cleanup
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


@lru_cache
def get_sandy_service() -> SandyService:
    """Get cached Sandy service instance."""
    return SandyService(get_settings())
