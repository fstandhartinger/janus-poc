"""Arena mode services for pairing competitors and tracking prompts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import random
from typing import Optional
from uuid import uuid4

from janus_gateway.services.competitor_registry import CompetitorRegistry


def hash_prompt(prompt: str) -> str:
    normalized = " ".join(prompt.split()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class ArenaPrompt:
    prompt_id: str
    prompt: str
    prompt_hash: str
    model_a: str
    model_b: str
    created_at: datetime
    user_id: Optional[str]
    voted: bool = False


class ArenaPromptStore:
    """In-memory store for arena prompt assignments."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._prompts: dict[str, ArenaPrompt] = {}

    def _prune(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [
            prompt_id
            for prompt_id, prompt in self._prompts.items()
            if now - prompt.created_at > self._ttl
        ]
        for prompt_id in expired:
            self._prompts.pop(prompt_id, None)

    def create(self, prompt: str, model_a: str, model_b: str, user_id: Optional[str]) -> ArenaPrompt:
        self._prune()
        prompt_id = f"arena-{uuid4().hex[:16]}"
        prompt_hash = hash_prompt(prompt)
        record = ArenaPrompt(
            prompt_id=prompt_id,
            prompt=prompt,
            prompt_hash=prompt_hash,
            model_a=model_a,
            model_b=model_b,
            created_at=datetime.now(timezone.utc),
            user_id=user_id,
        )
        self._prompts[prompt_id] = record
        return record

    def get(self, prompt_id: str) -> Optional[ArenaPrompt]:
        self._prune()
        return self._prompts.get(prompt_id)

    def mark_voted(self, prompt_id: str) -> None:
        prompt = self._prompts.get(prompt_id)
        if prompt:
            prompt.voted = True


class ArenaService:
    """Helper for pairing competitors for arena mode."""

    def __init__(self, registry: CompetitorRegistry) -> None:
        self._registry = registry

    def list_models(self, exclude: Optional[str] = None) -> list[str]:
        models = [competitor.id for competitor in self._registry.list_all()]
        if exclude:
            models = [model for model in models if model != exclude]
        return models

    def get_arena_pair(self, exclude: Optional[str] = None) -> tuple[str, str]:
        available = self.list_models(exclude=exclude)
        if len(available) < 2:
            raise ValueError("Need at least 2 models for arena")
        pair = random.sample(available, 2)
        random.shuffle(pair)
        return pair[0], pair[1]
