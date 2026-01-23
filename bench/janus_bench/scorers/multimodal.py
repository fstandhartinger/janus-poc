"""Multimodal handling scoring for benchmark responses."""

from __future__ import annotations

import base64
import io
import re
from functools import lru_cache
from typing import Any, Optional

import httpx

from .clip_evaluator import CLIPEvaluator


_IMAGE_DATA_RE = re.compile(r"data:image/(?P<format>[^;]+);base64,(?P<data>[A-Za-z0-9+/=]+)")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((https?://[^\)]+)\)")
_URL_IMAGE_RE = re.compile(r"https?://[^\s]+\.(?:png|jpg|jpeg|webp|gif)", re.IGNORECASE)


def score_multimodal(
    response_text: Optional[str],
    has_image_input: bool,
    expected_keywords: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
    prompt: Optional[str] = None,
) -> float:
    """Score multimodal handling based on task subtype metadata."""
    response = (response_text or "").strip()
    if not response:
        return 0.0

    metadata = metadata or {}
    evaluation = metadata.get("evaluation") or {}
    task_type = (
        metadata.get("multimodal_task_type")
        or metadata.get("task_type")
        or "multimodal"
    )

    if task_type == "image_generation":
        return _score_image_generation(response, evaluation, prompt)

    if task_type == "image_understanding":
        expected = list(evaluation.get("expected_elements") or [])
        min_matches = int(evaluation.get("min_matches", 1))
        return _score_key_facts(response, expected, min_matches)

    if task_type == "mixed_media":
        return _score_mixed_media(response, evaluation)

    if task_type == "modality_routing":
        expected_behavior = metadata.get("expected_behavior") or evaluation.get(
            "expected_behavior"
        )
        return _score_modality_routing(response, expected_behavior, evaluation)

    return _score_image_acknowledgement(response, has_image_input, expected_keywords)


def _score_image_generation(
    response: str,
    evaluation: dict[str, Any],
    prompt: Optional[str],
) -> float:
    candidates = _extract_image_candidates(response)
    if not candidates:
        return 0.0

    format_check = evaluation.get("check_format")
    allowed_formats = _parse_allowed_formats(format_check)

    candidate = _select_best_candidate(candidates)
    if allowed_formats and candidate.get("format"):
        if candidate["format"].lower() not in allowed_formats:
            return 0.2

    clip = _get_clip_evaluator()
    if clip is None:
        return 0.8

    image = _load_image(candidate)
    if image is None:
        return 0.7

    reference_prompt = evaluation.get("reference_prompt") or prompt or ""
    if not reference_prompt:
        return 0.7

    try:
        clip_score = clip.evaluate(image, reference_prompt)
    except Exception:
        return 0.7

    min_score = float(evaluation.get("min_score", 0.2))
    if clip_score >= min_score:
        return 1.0
    return 0.5


def _score_key_facts(response: str, expected: list[str], min_matches: int) -> float:
    if not expected:
        return 0.5
    response_lower = response.lower()
    matches = [item for item in expected if item.lower() in response_lower]
    if len(matches) >= min_matches:
        return 1.0
    if matches and min_matches > 0:
        return len(matches) / min_matches
    return 0.0


def _score_mixed_media(response: str, evaluation: dict[str, Any]) -> float:
    eval_type = evaluation.get("type", "contains_any")
    expected = list(evaluation.get("expected") or [])
    if not expected:
        return 0.5

    if eval_type == "contains_any":
        response_lower = response.lower()
        for candidate in expected:
            if candidate.lower() in response_lower:
                return 1.0
        return 0.0

    return 0.5


def _score_modality_routing(
    response: str,
    expected_behavior: Optional[str],
    evaluation: dict[str, Any],
) -> float:
    indicators = evaluation.get("indicators") or {}
    if not expected_behavior or not indicators:
        return 0.0

    response_lower = response.lower()

    expected_indicators = indicators.get(expected_behavior, [])
    for indicator in expected_indicators:
        if indicator.lower() in response_lower:
            return 1.0

    for behavior, behavior_indicators in indicators.items():
        if behavior == expected_behavior:
            continue
        for indicator in behavior_indicators:
            if indicator.lower() in response_lower:
                return 0.0

    return 0.5


def _score_image_acknowledgement(
    response: str,
    has_image_input: bool,
    expected_keywords: Optional[list[str]] = None,
) -> float:
    if not has_image_input:
        return 1.0

    response_lower = response.lower()

    image_acknowledgment_terms = [
        "image",
        "picture",
        "photo",
        "see",
        "shows",
        "appears",
        "visible",
        "display",
        "color",
        "pixel",
    ]

    acknowledged_image = any(term in response_lower for term in image_acknowledgment_terms)

    if not acknowledged_image:
        return 0.2

    if expected_keywords:
        matches = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
        return 0.5 + 0.5 * (matches / len(expected_keywords))

    return 0.8


def _extract_image_candidates(response: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []

    for match in _IMAGE_DATA_RE.finditer(response):
        candidates.append(
            {
                "type": "base64",
                "data": match.group("data"),
                "format": match.group("format"),
            }
        )

    for match in _MARKDOWN_IMAGE_RE.finditer(response):
        url = match.group(1)
        candidates.append(
            {
                "type": "url",
                "data": url,
                "format": _extract_url_format(url),
            }
        )

    for match in _URL_IMAGE_RE.finditer(response):
        url = match.group(0)
        candidates.append(
            {
                "type": "url",
                "data": url,
                "format": _extract_url_format(url),
            }
        )

    return candidates


def _select_best_candidate(candidates: list[dict[str, str]]) -> dict[str, str]:
    for candidate in candidates:
        if candidate.get("type") == "base64":
            return candidate
    return candidates[0]


def _parse_allowed_formats(value: Optional[str]) -> set[str]:
    if not value:
        return set()
    return {part.strip().lower() for part in value.split("|") if part.strip()}


def _extract_url_format(url: str) -> str:
    if not url:
        return ""
    trimmed = url.split("?")[0].split("#")[0]
    if "." not in trimmed:
        return ""
    return trimmed.rsplit(".", 1)[-1].lower()


def _load_image(candidate: dict[str, str]) -> Any | None:
    try:
        from PIL import Image
    except Exception:
        return None

    if candidate.get("type") == "base64":
        try:
            image_bytes = base64.b64decode(candidate.get("data", ""))
        except Exception:
            return None
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
            return image
        except Exception:
            return None

    if candidate.get("type") == "url":
        url = candidate.get("data", "")
        if not url:
            return None
        try:
            response = httpx.get(url, timeout=10.0, follow_redirects=True)
        except Exception:
            return None
        if response.status_code != 200:
            return None
        try:
            image = Image.open(io.BytesIO(response.content))
            image.load()
            return image
        except Exception:
            return None

    return None


@lru_cache(maxsize=1)
def _get_clip_evaluator() -> CLIPEvaluator | None:
    try:
        return CLIPEvaluator()
    except Exception:
        return None
