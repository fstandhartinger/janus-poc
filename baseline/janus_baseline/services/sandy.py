"""Sandy sandbox service for complex path execution."""

import asyncio
import uuid
from functools import lru_cache
from typing import AsyncGenerator, Optional

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

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.sandy_base_url
        self._api_key = settings.sandy_api_key
        self._timeout = settings.sandy_timeout

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
                            reasoning_content="Note: Sandy is not configured. Running in mock mode.\n"
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
                            content=f"I would execute this complex task in a Sandy sandbox:\n\n**Task:** {task}\n\nSandy is not currently configured, so I cannot execute code. Please configure SANDY_BASE_URL to enable sandbox execution."
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

        async with httpx.AsyncClient() as client:
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
                # Execute the task (simplified - in production would use a CLI agent)
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(reasoning_content=f"Executing task: {task[:100]}...\n")
                        )
                    ],
                )

                # Simple echo command as placeholder
                stdout, stderr, exit_code = await self._exec_in_sandbox(
                    client, sandbox_id, f'echo "Task received: {task[:50]}"'
                )

                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(
                                reasoning_content=f"Execution complete (exit code: {exit_code})\n"
                            )
                        )
                    ],
                )

                # Return result
                result = f"Executed in Sandy sandbox {sandbox_id}.\n\n"
                if stdout:
                    result += f"**Output:**\n```\n{stdout}\n```\n\n"
                if stderr:
                    result += f"**Errors:**\n```\n{stderr}\n```\n\n"

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
