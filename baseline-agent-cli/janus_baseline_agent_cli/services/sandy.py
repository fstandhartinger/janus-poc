"""Sandy sandbox service for complex path execution."""

import asyncio
import base64
import shlex
import uuid
from functools import lru_cache
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional

import httpx
import structlog

from janus_baseline.config import Settings, get_settings
from janus_baseline.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChunkChoice,
    Delta,
    FinishReason,
    MessageRole,
    Usage,
)

logger = structlog.get_logger()


class SandyService:
    """Service for executing tasks in Sandy sandboxes."""

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

    def _build_agent_env(self) -> dict[str, str]:
        """Build environment variables for the CLI agent."""
        return {
            "JANUS_AGENT_PACK": self._agent_pack_dest_root(),
            "JANUS_DOCS_ROOT": "/workspace/docs/models",
            "JANUS_SYSTEM_PROMPT_PATH": "/agent-pack/prompts/system.md",
            "JANUS_ENABLE_WEB_SEARCH": "1" if self._settings.enable_web_search else "0",
            "JANUS_ENABLE_CODE_EXECUTION": "1"
            if self._settings.enable_code_execution
            else "0",
            "JANUS_ENABLE_FILE_TOOLS": "1" if self._settings.enable_file_tools else "0",
        }

    def _build_agent_command(self, task: str) -> str:
        """Build the CLI agent command."""
        env_parts = [f"{key}={value}" for key, value in self._build_agent_env().items()]
        quoted_task = shlex.quote(task)
        return " ".join(
            [
                "env",
                *env_parts,
                "python",
                f"{self._agent_pack_dest_root()}/run_agent.py",
                quoted_task,
            ]
        )

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
        self, client: httpx.AsyncClient, sandbox_id: str
    ) -> tuple[str, str, int]:
        """Run the agent pack bootstrap script inside the sandbox."""
        command = f"bash {self._agent_pack_dest_root()}/bootstrap.sh"
        return await self._exec_in_sandbox(client, sandbox_id, command)

    async def _create_sandbox(self, client: httpx.AsyncClient) -> Optional[str]:
        """Create a new Sandy sandbox."""
        try:
            response = await client.post(
                f"{self._base_url}/api/sandboxes",
                json={
                    "priority": "NORMAL",
                    "ttl_seconds": self._timeout,
                },
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("sandbox_id") or data.get("id")
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
                json={"command": command},
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
                if isinstance(msg.content, str):
                    return msg.content
                # Handle list of content parts
                for part in msg.content:
                    if hasattr(part, "text"):
                        return part.text
                    elif isinstance(part, dict) and part.get("type") == "text":
                        return part.get("text", "")
        return "No task specified"

    async def execute_complex(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Execute a complex task using Sandy sandbox."""
        request_id = self._generate_id()
        model = request.model
        task = self._extract_task(request)

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
            sandbox_id = await self._create_sandbox(client)

            if not sandbox_id:
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

                bootstrap_stdout, bootstrap_stderr, bootstrap_exit = (
                    await self._run_bootstrap(client, sandbox_id)
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
                            delta=Delta(reasoning_content="Launching CLI agent...\n")
                        )
                    ],
                )

                command = self._build_agent_command(task)
                stdout, stderr, exit_code = await self._exec_in_sandbox(
                    client, sandbox_id, command
                )

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

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[ChunkChoice(delta=Delta(content=result))],
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
