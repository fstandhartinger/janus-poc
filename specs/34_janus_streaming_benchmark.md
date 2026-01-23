# Spec 34: Janus Streaming Benchmark

## Status: DRAFT

## Context / Why

Streaming response quality is critical for user experience in Janus Chat. Users expect:
- **Fast first token** - Quick acknowledgment that processing has started
- **Continuous flow** - Steady stream of tokens, not big batches
- **Smooth delivery** - Consistent inter-token timing
- **Complete responses** - All content delivered without truncation

The Janus Streaming Benchmark measures:
1. **TTFT** - Time to first token
2. **TPS** - Tokens per second throughput
3. **Continuity** - Regularity of token delivery
4. **Completeness** - Response completion rate

This benchmark contributes to both "Speed" (20%) and "Streaming" (15%) scoring categories.

## Goals

- Measure time-to-first-token (TTFT) accurately
- Calculate tokens-per-second (TPS) throughput
- Evaluate streaming continuity and smoothness
- Detect batching, stalling, and irregular delivery
- Provide reproducible metrics for competition

## Non-Goals

- Testing response quality (covered by other benchmarks)
- Testing reasoning capabilities
- Evaluating content correctness
- Audio/video streaming

## Functional Requirements

### FR-1: Metrics Definitions

#### Time to First Token (TTFT)

```python
@dataclass
class TTFTMetric:
    """Time from request sent to first token received."""
    value_ms: int
    percentile_90: int
    percentile_95: int
    percentile_99: int

def calculate_ttft(start_time: float, first_token_time: float) -> int:
    """Calculate TTFT in milliseconds."""
    return int((first_token_time - start_time) * 1000)
```

#### Tokens Per Second (TPS)

```python
@dataclass
class TPSMetric:
    """Tokens generated per second during streaming."""
    avg_tps: float
    peak_tps: float
    min_tps: float
    total_tokens: int
    total_time_ms: int

def calculate_tps(tokens: list[str], timestamps: list[float]) -> TPSMetric:
    """Calculate TPS metrics from token stream."""
    if len(tokens) < 2:
        return TPSMetric(0, 0, 0, len(tokens), 0)

    total_time = timestamps[-1] - timestamps[0]
    avg_tps = len(tokens) / total_time if total_time > 0 else 0

    # Calculate per-second rates
    window_rates = []
    for i in range(len(timestamps) - 1):
        delta = timestamps[i+1] - timestamps[i]
        if delta > 0:
            window_rates.append(1 / delta)

    return TPSMetric(
        avg_tps=avg_tps,
        peak_tps=max(window_rates) if window_rates else 0,
        min_tps=min(window_rates) if window_rates else 0,
        total_tokens=len(tokens),
        total_time_ms=int(total_time * 1000)
    )
```

#### Continuity Score

```python
@dataclass
class ContinuityMetric:
    """Measure of streaming smoothness (0-1)."""
    score: float  # 0-1, higher is smoother
    gap_count: int  # Number of significant gaps
    max_gap_ms: int  # Longest gap between tokens
    coefficient_of_variation: float  # CV of inter-token times

def calculate_continuity(timestamps: list[float]) -> ContinuityMetric:
    """
    Calculate continuity score based on inter-token timing variance.

    A perfect stream has consistent timing between tokens.
    Batching creates spikes of tokens followed by gaps.
    """
    if len(timestamps) < 3:
        return ContinuityMetric(1.0, 0, 0, 0.0)

    # Calculate inter-token times
    deltas = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]
    deltas_ms = [d * 1000 for d in deltas]

    mean_delta = sum(deltas_ms) / len(deltas_ms)
    variance = sum((d - mean_delta) ** 2 for d in deltas_ms) / len(deltas_ms)
    std_dev = variance ** 0.5
    cv = std_dev / mean_delta if mean_delta > 0 else 0

    # Count significant gaps (>3x mean)
    gap_threshold = mean_delta * 3
    gaps = [d for d in deltas_ms if d > gap_threshold]

    # Score: penalize high CV and many gaps
    # CV of 0 = perfect (score 1), CV of 2 = poor (score ~0.3)
    cv_score = 1 / (1 + cv)

    # Gap penalty: each gap reduces score
    gap_penalty = 1 - (len(gaps) * 0.1)  # 10% penalty per gap
    gap_penalty = max(0, gap_penalty)

    score = cv_score * gap_penalty

    return ContinuityMetric(
        score=min(1.0, max(0.0, score)),
        gap_count=len(gaps),
        max_gap_ms=int(max(deltas_ms)) if deltas_ms else 0,
        coefficient_of_variation=cv
    )
```

### FR-2: Task Types

The benchmark includes three task types:

#### 1. Short Response (20 items)

Test TTFT and basic streaming:

```json
{
  "id": "short_001",
  "task_type": "short_response",
  "prompt": "What is 2 + 2?",
  "expected_length": "short",
  "evaluation": {
    "ttft_target_ms": 500,
    "min_tokens": 5
  }
}
```

#### 2. Long Response (20 items)

Test sustained TPS and continuity:

```json
{
  "id": "long_001",
  "task_type": "long_response",
  "prompt": "Write a detailed explanation of how photosynthesis works, including the light and dark reactions.",
  "expected_length": "long",
  "evaluation": {
    "min_tokens": 200,
    "tps_target": 15,
    "continuity_target": 0.6
  }
}
```

#### 3. Reasoning Response (10 items)

Test streaming during complex reasoning:

```json
{
  "id": "reason_001",
  "task_type": "reasoning_response",
  "prompt": "Solve this step by step: If a train travels 120 miles in 2 hours, then stops for 30 minutes, then travels 60 more miles in 1 hour, what is the average speed for the entire journey?",
  "expected_length": "medium",
  "evaluation": {
    "check_reasoning_content": true,
    "ttft_target_ms": 1000
  }
}
```

### FR-3: Adapter Implementation

```python
# backend/app/benchmarks/adapters/janus_streaming.py

import asyncio
import json
import time
from dataclasses import asdict
from typing import AsyncIterator
from pathlib import Path

from app.benchmarks.base import BenchmarkAdapter, ItemResult
from app.benchmarks.registry import register_adapter


@register_adapter("janus_streaming")
class JanusStreamingAdapter(BenchmarkAdapter):
    """Benchmark for streaming response quality."""

    def __init__(self, client, model_slug, judge_client=None):
        super().__init__(client, model_slug, judge_client)
        self._items: list[dict] = []

    def get_name(self) -> str:
        return "janus_streaming"

    def get_display_name(self) -> str:
        return "Janus Streaming"

    def get_category(self) -> str:
        return "Janus Intelligence"

    async def get_total_items(self) -> int:
        if not self._items:
            await self.preload()
        return len(self._items)

    async def preload(self) -> None:
        data_path = Path(__file__).parent.parent / "data" / "janus" / "streaming_items.json"
        if data_path.exists():
            with open(data_path) as f:
                data = json.load(f)
                self._items = data.get("items", [])

    async def enumerate_items(self) -> AsyncIterator[str]:
        if not self._items:
            await self.preload()
        for item in self._items:
            yield item["id"]

    async def evaluate_item(self, item_id: str) -> ItemResult:
        """Evaluate streaming performance for a single item."""
        item = next((i for i in self._items if i["id"] == item_id), None)
        if not item:
            return ItemResult(item_id=item_id, error=f"Item {item_id} not found")

        prompt = item.get("prompt", "")
        evaluation = item.get("evaluation", {})

        # Track streaming metrics
        tokens: list[str] = []
        timestamps: list[float] = []
        first_token_time: float | None = None
        reasoning_content: str = ""
        content: str = ""

        try:
            start_time = time.time()

            # Stream the response
            async for chunk in self.client.chat_completion_stream(
                model=self.model_slug,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            ):
                now = time.time()

                delta = chunk.choices[0].delta if chunk.choices else None
                if delta:
                    # Track first token time
                    if first_token_time is None and (delta.content or delta.reasoning_content):
                        first_token_time = now

                    # Collect content
                    if delta.content:
                        content += delta.content
                        tokens.append(delta.content)
                        timestamps.append(now)

                    if delta.reasoning_content:
                        reasoning_content += delta.reasoning_content

            total_time = time.time() - start_time

        except Exception as e:
            return ItemResult(
                item_id=item_id,
                prompt=prompt,
                error=str(e)
            )

        # Calculate metrics
        ttft_ms = calculate_ttft(start_time, first_token_time) if first_token_time else None
        tps_metric = calculate_tps(tokens, timestamps)
        continuity_metric = calculate_continuity(timestamps)

        # Score the response
        score, reasoning = self._calculate_score(
            item=item,
            ttft_ms=ttft_ms,
            tps_metric=tps_metric,
            continuity_metric=continuity_metric,
            token_count=len(tokens),
            has_reasoning=bool(reasoning_content)
        )

        return ItemResult(
            item_id=item_id,
            item_hash=self.compute_item_hash(item),
            prompt=prompt,
            response=content[:500],  # Truncate for storage
            is_correct=score >= 0.7,
            score=score,
            judge_output={
                "reasoning": reasoning,
                "ttft_ms": ttft_ms,
                "tps": asdict(tps_metric),
                "continuity": asdict(continuity_metric),
                "token_count": len(tokens),
                "total_time_ms": int(total_time * 1000),
                "has_reasoning_content": bool(reasoning_content)
            },
            latency_ms=int(total_time * 1000),
            output_tokens=len(tokens),
        )

    def _calculate_score(
        self,
        item: dict,
        ttft_ms: int | None,
        tps_metric: TPSMetric,
        continuity_metric: ContinuityMetric,
        token_count: int,
        has_reasoning: bool
    ) -> tuple[float, str]:
        """Calculate overall streaming score."""
        evaluation = item.get("evaluation", {})
        task_type = item.get("task_type", "")
        scores = []
        reasons = []

        # TTFT score (weight: 30%)
        ttft_target = evaluation.get("ttft_target_ms", 1000)
        if ttft_ms is not None:
            if ttft_ms <= ttft_target:
                ttft_score = 1.0
            elif ttft_ms <= ttft_target * 2:
                ttft_score = 0.7
            elif ttft_ms <= ttft_target * 3:
                ttft_score = 0.4
            else:
                ttft_score = 0.1
            scores.append(("ttft", ttft_score, 0.30))
            reasons.append(f"TTFT: {ttft_ms}ms (target: {ttft_target}ms)")
        else:
            scores.append(("ttft", 0.0, 0.30))
            reasons.append("TTFT: No first token received")

        # TPS score (weight: 30%)
        tps_target = evaluation.get("tps_target", 10)
        if tps_metric.avg_tps >= tps_target:
            tps_score = 1.0
        elif tps_metric.avg_tps >= tps_target * 0.5:
            tps_score = 0.7
        else:
            tps_score = max(0.1, tps_metric.avg_tps / tps_target)
        scores.append(("tps", tps_score, 0.30))
        reasons.append(f"TPS: {tps_metric.avg_tps:.1f} (target: {tps_target})")

        # Continuity score (weight: 25%)
        continuity_target = evaluation.get("continuity_target", 0.5)
        if continuity_metric.score >= continuity_target:
            cont_score = 1.0
        else:
            cont_score = continuity_metric.score / continuity_target
        scores.append(("continuity", cont_score, 0.25))
        reasons.append(f"Continuity: {continuity_metric.score:.2f} (target: {continuity_target})")

        # Completion score (weight: 15%)
        min_tokens = evaluation.get("min_tokens", 10)
        if token_count >= min_tokens:
            completion_score = 1.0
        else:
            completion_score = token_count / min_tokens
        scores.append(("completion", completion_score, 0.15))
        reasons.append(f"Tokens: {token_count} (min: {min_tokens})")

        # Reasoning content bonus for reasoning tasks
        if task_type == "reasoning_response" and evaluation.get("check_reasoning_content"):
            if has_reasoning:
                reasons.append("Reasoning content: Present (+bonus)")
                # Small bonus for having reasoning content
                scores.append(("reasoning_bonus", 1.0, 0.05))
            else:
                reasons.append("Reasoning content: Missing")

        # Calculate weighted average
        total_weight = sum(s[2] for s in scores)
        weighted_score = sum(s[1] * s[2] for s in scores) / total_weight if total_weight > 0 else 0

        return weighted_score, " | ".join(reasons)

    async def postprocess(self, results: list[ItemResult]) -> dict:
        """Compute aggregate streaming metrics."""
        ttft_values = []
        tps_values = []
        continuity_values = []

        for result in results:
            if result.error or not result.judge_output:
                continue

            output = result.judge_output
            if output.get("ttft_ms"):
                ttft_values.append(output["ttft_ms"])
            if output.get("tps", {}).get("avg_tps"):
                tps_values.append(output["tps"]["avg_tps"])
            if output.get("continuity", {}).get("score") is not None:
                continuity_values.append(output["continuity"]["score"])

        metrics = {
            "avg_ttft_ms": sum(ttft_values) / len(ttft_values) if ttft_values else None,
            "p90_ttft_ms": sorted(ttft_values)[int(len(ttft_values) * 0.9)] if len(ttft_values) >= 10 else None,
            "avg_tps": sum(tps_values) / len(tps_values) if tps_values else None,
            "avg_continuity": sum(continuity_values) / len(continuity_values) if continuity_values else None,
            "samples": len(ttft_values)
        }

        return metrics

    def supports_parallel_items(self) -> bool:
        return False  # Streaming tests should be sequential for accurate timing

    def get_item_timeout_seconds(self) -> int:
        return 120  # 2 minutes per item
```

### FR-4: Normalization Functions for Composite Scoring

```python
def normalize_ttft(ttft_ms: int, target_ms: int = 500, ceiling_ms: int = 5000) -> float:
    """
    Normalize TTFT to 0-1 score.

    Args:
        ttft_ms: Actual TTFT in milliseconds
        target_ms: Target TTFT for score of 1.0
        ceiling_ms: TTFT that gives score of 0.0

    Returns:
        Score 0.0-1.0
    """
    if ttft_ms <= target_ms:
        return 1.0
    if ttft_ms >= ceiling_ms:
        return 0.0

    # Linear interpolation between target and ceiling
    return 1.0 - (ttft_ms - target_ms) / (ceiling_ms - target_ms)


def normalize_tps(tps: float, target_tps: float = 30, min_tps: float = 5) -> float:
    """
    Normalize TPS to 0-1 score.

    Args:
        tps: Actual tokens per second
        target_tps: Target TPS for score of 1.0
        min_tps: TPS that gives score of 0.0

    Returns:
        Score 0.0-1.0
    """
    if tps >= target_tps:
        return 1.0
    if tps <= min_tps:
        return 0.0

    return (tps - min_tps) / (target_tps - min_tps)
```

### FR-5: Test Data Examples

```json
{
  "metadata": {
    "version": "1.0.0",
    "total_items": 50,
    "categories": {
      "short_response": 20,
      "long_response": 20,
      "reasoning_response": 10
    }
  },
  "items": [
    {
      "id": "short_001",
      "task_type": "short_response",
      "prompt": "What is the capital of France?",
      "expected_length": "short",
      "evaluation": {
        "ttft_target_ms": 500,
        "min_tokens": 5,
        "tps_target": 20
      }
    },
    {
      "id": "short_002",
      "task_type": "short_response",
      "prompt": "Name three primary colors",
      "expected_length": "short",
      "evaluation": {
        "ttft_target_ms": 500,
        "min_tokens": 5,
        "tps_target": 20
      }
    },
    {
      "id": "long_001",
      "task_type": "long_response",
      "prompt": "Explain the process of machine learning model training, including data preparation, feature engineering, model selection, training, validation, and deployment. Provide examples where helpful.",
      "expected_length": "long",
      "evaluation": {
        "ttft_target_ms": 1000,
        "min_tokens": 300,
        "tps_target": 15,
        "continuity_target": 0.5
      }
    },
    {
      "id": "long_002",
      "task_type": "long_response",
      "prompt": "Write a comprehensive guide to REST API design best practices, covering URL structure, HTTP methods, status codes, versioning, authentication, error handling, and documentation.",
      "expected_length": "long",
      "evaluation": {
        "ttft_target_ms": 1000,
        "min_tokens": 400,
        "tps_target": 15,
        "continuity_target": 0.5
      }
    },
    {
      "id": "reason_001",
      "task_type": "reasoning_response",
      "prompt": "A farmer has 15 chickens and 10 cows. Each chicken has 2 legs and each cow has 4 legs. How many legs are there in total? Show your reasoning step by step.",
      "expected_length": "medium",
      "evaluation": {
        "ttft_target_ms": 800,
        "min_tokens": 50,
        "tps_target": 10,
        "check_reasoning_content": true
      }
    }
  ]
}
```

## Non-Functional Requirements

### NFR-1: Timing Accuracy

- Timestamps accurate to millisecond
- Use monotonic clock for measurements
- Account for network latency

### NFR-2: Reproducibility

- Results should be consistent across runs
- Sequential evaluation (not parallel) for accurate timing
- Report variance in metrics

### NFR-3: Fair Comparison

- All implementations tested under same conditions
- Network conditions should be stable
- Warm-up requests before measurement

## Acceptance Criteria

- [ ] 50 streaming test items created
- [ ] TTFT measurement working accurately
- [ ] TPS calculation implemented
- [ ] Continuity scoring working
- [ ] Reasoning content detection
- [ ] Aggregate metrics in postprocess
- [ ] Normalization functions for composite scoring
- [ ] Sequential evaluation mode working

## Open Questions / Risks

1. **Network variance**: How do we account for network latency differences?
2. **Cold start**: Should we include warm-up requests before measurement?
3. **Batching detection**: How do we reliably detect batched streaming?
4. **Timeout handling**: What score for incomplete streams?

## Related Specs

- `specs/30_janus_benchmark_integration.md` - Speed (20%) and Streaming (15%) weights
- `specs/05_streaming_contract.md` - Streaming API contract
- `specs/competition/02_description_and_scoring.md` - Speed and streaming categories

## Files to Create

```
chutes-bench-runner/backend/app/benchmarks/
├── adapters/
│   └── janus_streaming.py         # Adapter implementation
└── data/
    └── janus/
        └── streaming_items.json   # Test data (50 items)
```
