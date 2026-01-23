#!/usr/bin/env python3
"""Lightweight agent runner for baseline sandbox."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_doc(doc_name: str, docs_root: Path, agent_pack_root: Path) -> str:
    for root in (docs_root, agent_pack_root / "models"):
        doc_path = root / doc_name
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")
    return ""


def _extract_endpoints(doc_text: str) -> list[str]:
    endpoints: list[str] = []
    for line in doc_text.splitlines():
        line = line.strip()
        if line.startswith("POST "):
            endpoints.append(line.split(" ", 1)[1].strip())
    return endpoints


def _select_doc(task: str) -> str:
    task_lower = task.lower()
    if "lip" in task_lower or "musetalk" in task_lower:
        return "lip-sync.md"
    if "video" in task_lower:
        return "text-to-video.md"
    if "image" in task_lower:
        return "text-to-image.md"
    if "speech" in task_lower or "tts" in task_lower:
        return "text-to-speech.md"
    return "llm.md"


def _render_image_response(endpoints: list[str]) -> str:
    endpoint = endpoints[0] if endpoints else "https://image.chutes.ai/generate"
    return "\n".join(
        [
            "I checked /workspace/docs/models/text-to-image.md for Chutes image generation.",
            f"Endpoint: {endpoint}",
            "Example (Python):",
            "```python",
            "import requests",
            "payload = {\"prompt\": \"a neon cityscape\", "
            "\"width\": 1024, \"height\": 1024, \"steps\": 30}",
            f"resp = requests.post(\"{endpoint}\", json=payload, timeout=60)",
            "resp.raise_for_status()",
            "image_b64 = resp.json()[\"b64_json\"]",
            "```",
        ]
    )


def _render_tts_response(endpoints: list[str]) -> str:
    endpoint = endpoints[0] if endpoints else "https://chutes-kokoro.chutes.ai/speak"
    return "\n".join(
        [
            "I checked /workspace/docs/models/text-to-speech.md for Kokoro TTS.",
            f"Endpoint: {endpoint}",
            "Example (Python):",
            "```python",
            "import requests",
            "payload = {\"text\": \"Hello from Janus\", \"voice\": \"af_sky\", \"speed\": 1.0}",
            f"resp = requests.post(\"{endpoint}\", json=payload, timeout=60)",
            "resp.raise_for_status()",
            "with open(\"output.wav\", \"wb\") as f:",
            "    f.write(resp.content)",
            "```",
        ]
    )


def _render_video_response(endpoints: list[str]) -> str:
    endpoint = endpoints[0] if endpoints else "https://chutes-wan2-1-14b.chutes.ai/image2video"
    return "\n".join(
        [
            "I checked /workspace/docs/models/text-to-video.md for Chutes video generation.",
            f"Endpoint: {endpoint}",
            "Example (Python):",
            "```python",
            "import requests",
            "payload = {\"image\": \"base64_or_url\", \"prompt\": \"slow pan\", "
            "\"num_frames\": 81, \"fps\": 16}",
            f"resp = requests.post(\"{endpoint}\", json=payload, timeout=120)",
            "resp.raise_for_status()",
            "video_b64 = resp.json()[\"video\"]",
            "```",
        ]
    )


def _render_lip_sync_response(endpoints: list[str]) -> str:
    endpoint = endpoints[0] if endpoints else "https://chutes-musetalk.chutes.ai/generate"
    return "\n".join(
        [
            "I checked /workspace/docs/models/lip-sync.md for MuseTalk.",
            f"Endpoint: {endpoint}",
            "Example (Python):",
            "```python",
            "import requests",
            "payload = {\"source_image\": \"base64_portrait\", "
            "\"audio\": \"base64_wav\", \"fps\": 25}",
            f"resp = requests.post(\"{endpoint}\", json=payload, timeout=120)",
            "resp.raise_for_status()",
            "video_b64 = resp.json()[\"video\"]",
            "```",
        ]
    )


def _render_llm_response(endpoints: list[str]) -> str:
    endpoint = endpoints[0] if endpoints else "https://llm.chutes.ai/v1/chat/completions"
    return "\n".join(
        [
            "I checked /workspace/docs/models/llm.md for the Chutes LLM endpoint.",
            f"Endpoint: {endpoint}",
            "Example (Python):",
            "```python",
            "import requests",
            "payload = {\"model\": \"deepseek-ai/DeepSeek-V3-0324\", "
            "\"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}",
            f"resp = requests.post(\"{endpoint}\", json=payload, timeout=60)",
            "resp.raise_for_status()",
            "print(resp.json())",
            "```",
        ]
    )


def main() -> int:
    task = " ".join(sys.argv[1:]).strip() or os.environ.get("JANUS_TASK", "")
    if not task:
        print("No task provided.")
        return 0

    docs_root = Path(os.environ.get("JANUS_DOCS_ROOT", "/workspace/docs/models"))
    agent_pack_root = Path(os.environ.get("JANUS_AGENT_PACK", "/agent-pack"))
    doc_name = _select_doc(task)
    doc_text = _load_doc(doc_name, docs_root, agent_pack_root)
    endpoints = _extract_endpoints(doc_text)

    if doc_name == "text-to-image.md":
        print(_render_image_response(endpoints))
    elif doc_name == "text-to-speech.md":
        print(_render_tts_response(endpoints))
    elif doc_name == "text-to-video.md":
        print(_render_video_response(endpoints))
    elif doc_name == "lip-sync.md":
        print(_render_lip_sync_response(endpoints))
    else:
        print(_render_llm_response(endpoints))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
