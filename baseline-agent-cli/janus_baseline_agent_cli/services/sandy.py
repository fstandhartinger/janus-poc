"""Sandy sandbox service for complex path execution."""

import asyncio
import base64
import hashlib
import json
import mimetypes
import shlex
import uuid
from functools import lru_cache
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional

import httpx
import structlog

from janus_baseline_agent_cli.config import Settings, get_settings
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
    Message,
    MessageRole,
    Usage,
)
from janus_baseline_agent_cli.services.vision import contains_images, get_image_urls
from janus_baseline_agent_cli.services.response_processor import process_agent_response

logger = structlog.get_logger()


class SandyService:
    """Service for executing tasks in Sandy sandboxes."""

    _max_inline_bytes = 1_000_000
    _default_path = "/agent-pack/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

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
        chutes_api_key = self._settings.chutes_api_key or self._settings.openai_api_key or ""
        chutes_api_url = self._settings.openai_base_url or "https://api.chutes.ai/v1"
        auth_token = self._resolve_auth_token(request)
        return {
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

    def _resolve_auth_token(self, request: ChatCompletionRequest | None) -> str | None:
        if request is None:
            return self._settings.sandy_api_key
        auth_token = getattr(request, "_auth_token", None)
        return auth_token or self._settings.sandy_api_key

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
        env_parts = [
            f"{key}={shlex.quote(str(value))}"
            for key, value in self._build_agent_env(
                sandbox_id, public_url, request, has_images
            ).items()
        ]
        quoted_task = shlex.quote(task)
        if agent == "builtin":
            command = [
                "python",
                f"{self._agent_pack_dest_root()}/run_agent.py",
                quoted_task,
            ]
        else:
            command = [agent, quoted_task]
        return " ".join(["env", *env_parts, *command])

    def _agent_candidates(self) -> list[str]:
        """Determine preferred agent order."""
        requested = self._baseline_agent.strip().lower()
        if requested in {"builtin", "run_agent"}:
            return ["builtin"]
        if requested:
            return [requested, "openhands", "opencode", "builtin"]
        return ["aider", "openhands", "opencode", "builtin"]

    async def _select_agent(
        self,
        client: httpx.AsyncClient,
        sandbox_id: str,
    ) -> str:
        """Pick an available CLI agent inside the sandbox."""
        for candidate in self._agent_candidates():
            if candidate == "builtin":
                return "builtin"
            stdout, _, exit_code = await self._exec_in_sandbox(
                client,
                sandbox_id,
                f"PATH={shlex.quote(self._default_path)} command -v {shlex.quote(candidate)}",
            )
            if exit_code == 0 and stdout.strip():
                return candidate
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
                "priority": "NORMAL",
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
            sandbox_id = data.get("sandbox_id") or data.get("id")
            if sandbox_id is None:
                return None
            public_url = data.get("public_url") or data.get("sandbox_url")
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

    def _generate_id(self) -> str:
        """Generate a completion ID."""
        return f"chatcmpl-baseline-sandy-{uuid.uuid4().hex[:12]}"

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

                return task_text
        return "No task specified"

    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Execute a complex task and return a non-streaming response."""
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)
        has_images = contains_images(request.messages)

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

        sandbox_start = asyncio.get_event_loop().time()

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
                        sandbox_seconds=asyncio.get_event_loop().time() - sandbox_start,
                    ),
                )

            finally:
                await self._terminate_sandbox(client, sandbox_id)

    async def execute_complex(
        self,
        request: ChatCompletionRequest,
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

        sandbox_start = asyncio.get_event_loop().time()

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

                sandbox_seconds = asyncio.get_event_loop().time() - sandbox_start

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
