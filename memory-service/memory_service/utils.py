import hashlib
import json
from typing import Iterable

from nanoid import generate


def generate_memory_id() -> str:
    return f"mem_{generate(size=16)}"


def hash_conversation(conversation: Iterable[dict]) -> str:
    payload = json.dumps(conversation, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    if max_length <= 3:
        return value[:max_length]
    return value[: max_length - 3].rstrip() + "..."
