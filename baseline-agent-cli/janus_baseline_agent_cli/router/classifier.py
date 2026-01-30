"""LLM-based routing decision classifier for the composite router."""

from __future__ import annotations

import json

import httpx
import structlog

from janus_baseline_agent_cli.routing import (
    DECISION_MODEL_ID,
    ROUTING_DECISION_PROMPT,
    ROUTING_DECISION_TOOL,
    RoutingDecision,
    decision_for_images,
)

logger = structlog.get_logger()


class RoutingDecisionClassifier:
    """Classifies incoming requests to determine routing decision."""

    def __init__(self, api_key: str, api_base: str = "https://llm.chutes.ai/v1") -> None:
        self.api_key = api_key
        self.api_base = api_base
        self.model_id = DECISION_MODEL_ID
        self.client = httpx.AsyncClient(timeout=5.0)

    async def classify(
        self,
        messages: list[dict],
        has_images: bool = False,
    ) -> tuple[RoutingDecision, float]:
        """Classify a request to determine routing decision."""
        user_content = self._extract_user_content(messages)
        user_lower = user_content.lower().strip()

        if not user_content:
            return RoutingDecision.FAST_QWEN, 0.5

        if len(user_content) < 30:
            return RoutingDecision.FAST_QWEN, 0.9

        try:
            response = await self.client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_id,
                    "messages": [
                        {
                            "role": "user",
                            "content": ROUTING_DECISION_PROMPT.format(
                                user_message=user_content[:2000],
                                has_images=str(has_images).lower(),
                            ),
                        },
                    ],
                    "tools": [ROUTING_DECISION_TOOL],
                    "tool_choice": {
                        "type": "function",
                        "function": {"name": "select_routing_decision"},
                    },
                    "max_tokens": 80,
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            data = response.json()

            tool_calls = data.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
            if tool_calls:
                args = json.loads(tool_calls[0]["function"]["arguments"])
                decision = RoutingDecision(args["decision"])
                confidence = float(args.get("confidence", 0.7)) if isinstance(args, dict) else 0.7
                return decision, confidence
        except Exception as exc:
            logger.warning("router_classification_error", error=str(exc), text_preview=user_lower[:200])

        if has_images:
            return decision_for_images(False), 0.6
        return RoutingDecision.FAST_NEMOTRON, 0.6

    def _extract_user_content(self, messages: list[dict]) -> str:
        """Extract text content from user messages."""
        parts: list[str] = []
        for message in messages:
            if message.get("role") != "user":
                continue
            content = message.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
        return " ".join(parts)

    async def close(self) -> None:
        await self.client.aclose()
