import json
import logging
import re
from dataclasses import dataclass
from typing import Iterable, List

import httpx

from memory_service.config import get_settings
from memory_service.utils import truncate

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
You are a memory extraction assistant. Analyze this conversation and identify facts worth remembering about the user for future sessions.

Extract ONLY:
- Personal preferences (favorite things, dislikes)
- Important personal information (names, relationships, pets, locations)
- Technical preferences (coding style, tools they use)
- Ongoing projects or goals
- Specific facts they want to remember

DO NOT extract:
- Temporary context (what they're working on RIGHT NOW)
- General knowledge or facts
- Conversational pleasantries
- Things already commonly known

Return JSON array of memories to save:
[
  {
    "caption": "Brief 1-line summary (max 100 chars)",
    "full_text": "Full context with details (max 500 chars)"
  }
]

If nothing worth memorizing, return empty array: []

Conversation:
<conversation>
{conversation}
</conversation>
"""

RELEVANCE_PROMPT = """
You are a memory relevance assistant. Given a user's prompt and their stored memories, select which memories might be relevant to help answer their question.

User's prompt:
<prompt>
{prompt}
</prompt>

Available memories (id: caption):
<memories>
{memory_list}
</memories>

Return JSON array of relevant memory IDs, most relevant first. If none are relevant, return empty array: []

Example: ["mem_abc123", "mem_def456"]
"""


@dataclass(frozen=True)
class ExtractedMemory:
    caption: str
    full_text: str


async def extract_memories(conversation: Iterable[dict]) -> List[ExtractedMemory]:
    settings = get_settings()
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "user", "content": EXTRACTION_PROMPT.format(conversation=_format_json(conversation))}
        ],
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    content = await _call_llm(payload)
    memories = _parse_extracted_memories(content) if content else []
    if memories:
        return memories
    return _fallback_extract_memories(conversation)


async def select_relevant_ids(prompt: str, memories: Iterable[tuple[str, str]]) -> List[str]:
    settings = get_settings()
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "user",
                "content": RELEVANCE_PROMPT.format(
                    prompt=prompt,
                    memory_list="\n".join(f"{mem_id}: {caption}" for mem_id, caption in memories),
                ),
            }
        ],
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    content = await _call_llm(payload)
    ids = _parse_relevant_ids(content) if content else []
    if ids:
        return ids
    return _fallback_relevant_ids(prompt, memories)


def _format_json(conversation: Iterable[dict]) -> str:
    return json.dumps(list(conversation), ensure_ascii=False, separators=(",", ":"))


def _parse_extracted_memories(content: str) -> List[ExtractedMemory]:
    data = _extract_json_array(content)
    memories: List[ExtractedMemory] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        caption = str(item.get("caption", "")).strip()
        full_text = str(item.get("full_text", "")).strip()
        if not caption or not full_text:
            continue
        caption = truncate(caption, 100)
        full_text = truncate(full_text, 500)
        memories.append(ExtractedMemory(caption=caption, full_text=full_text))
    return memories


def _parse_relevant_ids(content: str) -> List[str]:
    data = _extract_json_array(content)
    ids: List[str] = []
    for value in data:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned:
            ids.append(cleaned)
    return ids


def _extract_json_array(content: str) -> list:
    start = content.find("[")
    end = content.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    snippet = content[start : end + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return parsed


async def _call_llm(payload: dict) -> str:
    settings = get_settings()
    if not settings.chutes_api_key:
        logger.warning("CHUTES_API_KEY missing; returning empty LLM response")
        return ""

    headers = {"Authorization": f"Bearer {settings.chutes_api_key}"}
    timeout = httpx.Timeout(settings.llm_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("LLM request failed: %s", exc)
            return ""

    try:
        data = response.json()
    except (ValueError, TypeError) as exc:
        logger.warning("LLM response JSON parse failed: %s", exc)
        return ""
    if not isinstance(data, dict):
        logger.warning("LLM response payload not a dict")
        return ""
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return str(message.get("content", "")).strip()


def _fallback_extract_memories(conversation: Iterable[dict]) -> List[ExtractedMemory]:
    """Fallback heuristic extraction when the LLM is unavailable."""
    memories: List[ExtractedMemory] = []
    seen: set[str] = set()
    for message in conversation:
        if message.get("role") != "user":
            continue
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        for sentence in _split_sentences(content):
            lowered = sentence.lower()
            if not _matches_memory_pattern(lowered):
                continue
            caption = truncate(sentence, 100)
            full_text = truncate(sentence, 500)
            key = caption.lower()
            if key in seen:
                continue
            seen.add(key)
            memories.append(ExtractedMemory(caption=caption, full_text=full_text))
    return memories


def _fallback_relevant_ids(
    prompt: str, memories: Iterable[tuple[str, str]]
) -> List[str]:
    """Fallback relevance matching based on token overlap."""
    prompt_tokens = _tokenize(prompt)
    if not prompt_tokens:
        return []
    ranked: list[tuple[int, str]] = []
    for mem_id, caption in memories:
        caption_tokens = _tokenize(caption)
        overlap = prompt_tokens & caption_tokens
        if overlap:
            ranked.append((len(overlap), mem_id))
    ranked.sort(reverse=True)
    return [mem_id for _, mem_id in ranked]


def _matches_memory_pattern(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "my favorite",
            "my name",
            "i am ",
            "i'm ",
            "i live",
            "remember",
        )
    )


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))
