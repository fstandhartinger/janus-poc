"""Arena mode endpoints for side-by-side comparisons."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import time
from typing import Deque, Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from janus_gateway.config import Settings, get_settings
from janus_gateway.models import (
    ArenaCompletionResponse,
    ArenaResponseMessage,
    ArenaVoteRequest,
    ArenaVoteResponse,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
)
from janus_gateway.services import ArenaPromptStore, ArenaService, MessageProcessor, get_competitor_registry
from janus_gateway.services.competitor_registry import CompetitorRegistry


router = APIRouter(tags=["arena"])
logger = structlog.get_logger()
message_processor = MessageProcessor()
prompt_store = ArenaPromptStore()

_vote_history: dict[str, Deque[float]] = defaultdict(deque)
_VOTE_WINDOW_SECONDS = 60 * 60
_VOTE_LIMIT = 50
_MIN_VIEW_SECONDS = 5
_MIN_SESSION_AGE_SECONDS = 60 * 60


def _get_prompt_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.content is None:
            continue
        if isinstance(message.content, str):
            if message.content.strip():
                return message.content
        if isinstance(message.content, list):
            parts = [
                part.text
                for part in message.content
                if hasattr(part, "text") and part.text
            ]
            if parts:
                return "\n".join(parts)
    return ""


def _extract_content(response: ChatCompletionResponse) -> str:
    if not response.choices:
        return ""
    message = response.choices[0].message
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [part.text for part in content if hasattr(part, "text") and part.text]
        return "\n".join(parts)
    return ""


def _check_rate_limit(key: str) -> None:
    now = time.monotonic()
    history = _vote_history[key]
    while history and now - history[0] > _VOTE_WINDOW_SECONDS:
        history.popleft()
    if len(history) >= _VOTE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many votes, slow down.")
    history.append(now)


def _session_age_seconds(created_at: int) -> Optional[float]:
    if not created_at:
        return None
    timestamp = created_at / 1000 if created_at > 1_000_000_000_000 else created_at
    return time.time() - timestamp


async def _fetch_competitor(
    client: httpx.AsyncClient,
    competitor_url: str,
    request: ChatCompletionRequest,
    settings: Settings,
) -> ChatCompletionResponse:
    response = await client.post(
        f"{competitor_url}/v1/chat/completions",
        json=request.model_dump(exclude_none=True, exclude={"competitor_id"}),
        timeout=settings.request_timeout,
    )
    if response.status_code != 200:
        error_text = response.text
        raise HTTPException(
            status_code=502,
            detail=f"Competitor error ({response.status_code}): {error_text[:200]}",
        )
    payload = response.json()
    return ChatCompletionResponse(**payload)


@router.post("/v1/chat/completions/arena", response_model=ArenaCompletionResponse)
async def arena_chat(
    request: ChatCompletionRequest,
    registry: CompetitorRegistry = Depends(get_competitor_registry),
    settings: Settings = Depends(get_settings),
) -> ArenaCompletionResponse:
    arena_service = ArenaService(registry)
    try:
        model_a, model_b = arena_service.get_arena_pair()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    processed_messages = [
        message_processor.process_message(message) for message in request.messages
    ]
    prompt_text = _get_prompt_text(processed_messages)
    processed_request = request.model_copy(
        update={"messages": processed_messages, "stream": False}
    )

    request_a = processed_request.model_copy(update={"model": model_a, "stream": False})
    request_b = processed_request.model_copy(update={"model": model_b, "stream": False})

    logger.info(
        "arena_request",
        model_a=model_a,
        model_b=model_b,
        message_count=len(processed_messages),
    )

    competitor_a = registry.get(model_a)
    competitor_b = registry.get(model_b)
    if not competitor_a or not competitor_b:
        raise HTTPException(status_code=400, detail="Arena models unavailable")

    async with httpx.AsyncClient() as client:
        response_a, response_b = await asyncio.gather(
            _fetch_competitor(client, competitor_a.url, request_a, settings),
            _fetch_competitor(client, competitor_b.url, request_b, settings),
        )

    prompt_record = prompt_store.create(
        prompt=prompt_text,
        model_a=model_a,
        model_b=model_b,
        user_id=request.user_id,
    )

    return ArenaCompletionResponse(
        prompt_id=prompt_record.prompt_id,
        response_a=ArenaResponseMessage(content=_extract_content(response_a)),
        response_b=ArenaResponseMessage(content=_extract_content(response_b)),
    )


@router.post("/api/arena/vote", response_model=ArenaVoteResponse)
async def submit_vote(
    vote: ArenaVoteRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ArenaVoteResponse:
    prompt = prompt_store.get(vote.prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if prompt.voted:
        raise HTTPException(status_code=409, detail="Vote already recorded")

    view_duration = datetime.now(timezone.utc) - prompt.created_at
    if view_duration < timedelta(seconds=_MIN_VIEW_SECONDS):
        raise HTTPException(status_code=400, detail="Vote submitted too quickly")

    client_id = vote.user_id or (request.client.host if request.client else "unknown")
    _check_rate_limit(client_id)

    if vote.user_id and vote.session_created_at:
        age_seconds = _session_age_seconds(vote.session_created_at)
        if age_seconds is not None and age_seconds < _MIN_SESSION_AGE_SECONDS:
            raise HTTPException(status_code=403, detail="Account too new to vote")

    payload = {
        "prompt_id": prompt.prompt_id,
        "winner": vote.winner,
        "model_a": prompt.model_a,
        "model_b": prompt.model_b,
        "user_id": vote.user_id,
        "prompt_hash": prompt.prompt_hash,
    }

    scoring_url = settings.scoring_service_url.rstrip("/")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{scoring_url}/api/arena/vote", json=payload)
        if response.status_code == 409:
            raise HTTPException(status_code=409, detail="Vote already recorded")
        if response.status_code >= 400:
            detail = response.text if response.text else "Scoring service error"
            raise HTTPException(status_code=502, detail=detail)

    prompt_store.mark_voted(prompt.prompt_id)
    return ArenaVoteResponse(
        status="recorded",
        model_a=prompt.model_a,
        model_b=prompt.model_b,
    )
