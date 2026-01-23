# Spec 35: Janus Cost Efficiency Benchmark

## Status: DRAFT

## Context / Why

Cost efficiency is a critical factor for Janus intelligence implementations in production. An implementation that achieves great quality but uses 10x the tokens of a simpler approach may not be economically viable. The Janus Cost Benchmark measures:

1. **Token efficiency** - Achieving goals with fewer input/output tokens
2. **Model selection** - Using cheaper models when appropriate
3. **Tool usage efficiency** - Minimizing redundant API calls
4. **Response conciseness** - Avoiding unnecessarily verbose responses

This benchmark contributes to the "Cost" scoring category (15% of composite score).

## Goals

- Measure token usage per task type
- Evaluate quality-to-cost ratio
- Track model selection efficiency
- Assess overall cost optimization
- Provide reproducible cost metrics

## Non-Goals

- Actual dollar cost calculation (varies by provider)
- Billing integration
- Real-time cost tracking during chat
- Hardware resource measurement

## Functional Requirements

### FR-1: Cost Metrics

#### Token Usage Metrics

```python
@dataclass
class TokenMetrics:
    """Token usage for a single task."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int  # Tokens in reasoning_content (if any)

@dataclass
class CostMetrics:
    """Cost metrics for evaluation."""
    avg_input_tokens: float
    avg_output_tokens: float
    avg_total_tokens: float
    token_efficiency_score: float  # Quality / tokens ratio
    conciseness_score: float  # 0-1, shorter good responses score higher
```

#### Cost Efficiency Calculation

```python
def calculate_cost_efficiency(
    quality_score: float,
    total_tokens: int,
    baseline_tokens: int
) -> float:
    """
    Calculate cost efficiency score.

    Higher quality with fewer tokens = better efficiency.

    Args:
        quality_score: Quality score 0-1 from evaluation
        total_tokens: Actual tokens used
        baseline_tokens: Expected baseline token usage

    Returns:
        Efficiency score 0-1
    """
    # Token ratio: how much better/worse than baseline
    token_ratio = baseline_tokens / total_tokens if total_tokens > 0 else 0

    # Cap token ratio at 2x (can't be "infinitely efficient")
    token_ratio = min(2.0, token_ratio)

    # Efficiency = quality * token_ratio (normalized)
    efficiency = quality_score * (token_ratio / 2)  # Normalize to 0-1

    return min(1.0, efficiency)
```

### FR-2: Task Types

The benchmark includes four task types:

#### 1. Concise Response (15 items)

Test ability to give brief, accurate answers:

```json
{
  "id": "concise_001",
  "task_type": "concise_response",
  "prompt": "What year did World War II end? Answer in one sentence.",
  "evaluation": {
    "type": "contains_and_length",
    "required": ["1945"],
    "max_words": 20,
    "baseline_tokens": 50
  }
}
```

#### 2. Efficient Explanation (10 items)

Test explanations without unnecessary verbosity:

```json
{
  "id": "explain_001",
  "task_type": "efficient_explanation",
  "prompt": "Explain what an API is in simple terms.",
  "evaluation": {
    "type": "quality_and_tokens",
    "quality_criteria": ["interface", "communicate", "applications"],
    "min_matches": 2,
    "baseline_tokens": 150,
    "max_tokens": 300
  }
}
```

#### 3. Minimal Tool Usage (10 items)

Test efficient tool/API call patterns:

```json
{
  "id": "tool_001",
  "task_type": "minimal_tools",
  "prompt": "What is 15% of 200?",
  "evaluation": {
    "type": "tool_count",
    "max_tool_calls": 1,
    "expected_answer_contains": ["30"],
    "baseline_tokens": 100
  }
}
```

#### 4. Direct Answer (5 items)

Test avoiding unnecessary preamble/explanation:

```json
{
  "id": "direct_001",
  "task_type": "direct_answer",
  "prompt": "Convert 100 USD to EUR at current rates",
  "evaluation": {
    "type": "directness",
    "answer_must_appear_within_first": 50,
    "baseline_tokens": 80
  }
}
```

### FR-3: Evaluation Methods

#### Contains and Length Check

```python
def evaluate_concise_response(
    response: str,
    required: list[str],
    max_words: int
) -> tuple[float, str]:
    """
    Evaluate concise response quality.

    Returns:
        (score, reasoning)
    """
    response_lower = response.lower()

    # Check required content
    found = sum(1 for req in required if req.lower() in response_lower)
    content_score = found / len(required) if required else 1.0

    # Check length
    word_count = len(response.split())
    if word_count <= max_words:
        length_score = 1.0
    elif word_count <= max_words * 2:
        length_score = 0.5
    else:
        length_score = 0.2

    score = (content_score * 0.7) + (length_score * 0.3)
    return score, f"Content: {content_score:.2f}, Length: {word_count} words"
```

#### Quality and Token Balance

```python
def evaluate_quality_and_tokens(
    response: str,
    output_tokens: int,
    quality_criteria: list[str],
    min_matches: int,
    baseline_tokens: int,
    max_tokens: int
) -> tuple[float, str]:
    """
    Balance quality vs token usage.
    """
    response_lower = response.lower()

    # Quality score
    matches = sum(1 for crit in quality_criteria if crit.lower() in response_lower)
    quality_score = matches / min_matches if matches >= min_matches else matches / min_matches * 0.7

    # Token efficiency
    if output_tokens <= baseline_tokens:
        token_score = 1.0
    elif output_tokens <= max_tokens:
        overage = output_tokens - baseline_tokens
        allowed_overage = max_tokens - baseline_tokens
        token_score = 1.0 - (overage / allowed_overage * 0.5)
    else:
        token_score = 0.3

    # Combined score
    score = (quality_score * 0.6) + (token_score * 0.4)

    return score, f"Quality: {quality_score:.2f}, Tokens: {output_tokens}/{baseline_tokens}"
```

### FR-4: Adapter Implementation

```python
# backend/app/benchmarks/adapters/janus_cost.py

import json
import time
from typing import AsyncIterator
from pathlib import Path

from app.benchmarks.base import BenchmarkAdapter, ItemResult
from app.benchmarks.registry import register_adapter


@register_adapter("janus_cost")
class JanusCostAdapter(BenchmarkAdapter):
    """Benchmark for cost efficiency and token optimization."""

    def __init__(self, client, model_slug, judge_client=None):
        super().__init__(client, model_slug, judge_client)
        self._items: list[dict] = []

    def get_name(self) -> str:
        return "janus_cost"

    def get_display_name(self) -> str:
        return "Janus Cost Efficiency"

    def get_category(self) -> str:
        return "Janus Intelligence"

    async def get_total_items(self) -> int:
        if not self._items:
            await self.preload()
        return len(self._items)

    async def preload(self) -> None:
        data_path = Path(__file__).parent.parent / "data" / "janus" / "cost_items.json"
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
        """Evaluate cost efficiency for a single item."""
        item = next((i for i in self._items if i["id"] == item_id), None)
        if not item:
            return ItemResult(item_id=item_id, error=f"Item {item_id} not found")

        prompt = item.get("prompt", "")
        task_type = item.get("task_type", "")
        evaluation = item.get("evaluation", {})

        try:
            start_time = time.time()

            response = await self.client.chat_completion(
                model=self.model_slug,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            response_text = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            # Count tool calls if any
            tool_calls = []
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = [tc.function.name for tc in message.tool_calls]

        except Exception as e:
            return ItemResult(
                item_id=item_id,
                prompt=prompt,
                error=str(e)
            )

        # Evaluate based on task type
        if task_type == "concise_response":
            score, reasoning = evaluate_concise_response(
                response_text,
                evaluation.get("required", []),
                evaluation.get("max_words", 50)
            )
        elif task_type == "efficient_explanation":
            score, reasoning = evaluate_quality_and_tokens(
                response_text,
                output_tokens,
                evaluation.get("quality_criteria", []),
                evaluation.get("min_matches", 1),
                evaluation.get("baseline_tokens", 100),
                evaluation.get("max_tokens", 200)
            )
        elif task_type == "minimal_tools":
            score, reasoning = self._evaluate_tool_efficiency(
                response_text,
                tool_calls,
                evaluation
            )
        elif task_type == "direct_answer":
            score, reasoning = self._evaluate_directness(
                response_text,
                evaluation
            )
        else:
            score, reasoning = 0.5, f"Unknown task type: {task_type}"

        # Calculate efficiency score
        baseline = evaluation.get("baseline_tokens", 100)
        efficiency = calculate_cost_efficiency(score, output_tokens, baseline)

        return ItemResult(
            item_id=item_id,
            item_hash=self.compute_item_hash(item),
            prompt=prompt,
            response=response_text[:500],
            is_correct=score >= 0.7,
            score=efficiency,  # Use efficiency as the main score
            judge_output={
                "reasoning": reasoning,
                "quality_score": score,
                "efficiency_score": efficiency,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "baseline_tokens": baseline,
                "tool_calls": tool_calls
            },
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _evaluate_tool_efficiency(
        self,
        response: str,
        tool_calls: list,
        evaluation: dict
    ) -> tuple[float, str]:
        """Evaluate minimal tool usage."""
        max_calls = evaluation.get("max_tool_calls", 1)
        expected = evaluation.get("expected_answer_contains", [])

        # Check answer correctness
        response_lower = response.lower()
        correct = any(exp.lower() in response_lower for exp in expected)

        # Check tool count
        efficient = len(tool_calls) <= max_calls

        if correct and efficient:
            return 1.0, f"Correct with {len(tool_calls)} tool calls"
        elif correct:
            return 0.6, f"Correct but used {len(tool_calls)} calls (max: {max_calls})"
        elif efficient:
            return 0.3, "Efficient but incorrect"
        else:
            return 0.1, f"Incorrect and used {len(tool_calls)} calls"

    def _evaluate_directness(
        self,
        response: str,
        evaluation: dict
    ) -> tuple[float, str]:
        """Evaluate answer directness (answer appears early)."""
        answer_within = evaluation.get("answer_must_appear_within_first", 50)

        # Check if response starts with relevant content
        words = response.split()
        first_words = " ".join(words[:answer_within])

        # Look for number patterns (for conversion tasks)
        import re
        numbers = re.findall(r'\d+\.?\d*', first_words)

        if numbers:
            return 1.0, f"Answer appears within first {answer_within} words"

        # Check full response for numbers
        all_numbers = re.findall(r'\d+\.?\d*', response)
        if all_numbers:
            return 0.5, "Answer present but not direct"

        return 0.2, "Answer unclear or missing"

    async def postprocess(self, results: list[ItemResult]) -> dict:
        """Compute aggregate cost metrics."""
        total_input = 0
        total_output = 0
        total_baseline = 0
        quality_scores = []
        efficiency_scores = []

        for result in results:
            if result.error or not result.judge_output:
                continue

            output = result.judge_output
            total_input += output.get("input_tokens", 0)
            total_output += output.get("output_tokens", 0)
            total_baseline += output.get("baseline_tokens", 0)
            quality_scores.append(output.get("quality_score", 0))
            efficiency_scores.append(output.get("efficiency_score", 0))

        n = len(quality_scores)
        metrics = {
            "avg_input_tokens": total_input / n if n > 0 else 0,
            "avg_output_tokens": total_output / n if n > 0 else 0,
            "total_tokens": total_input + total_output,
            "baseline_tokens": total_baseline,
            "avg_quality_score": sum(quality_scores) / n if n > 0 else 0,
            "avg_efficiency_score": sum(efficiency_scores) / n if n > 0 else 0,
            "token_savings_pct": ((total_baseline - total_output) / total_baseline * 100) if total_baseline > 0 else 0,
            "samples": n
        }

        return metrics

    def supports_parallel_items(self) -> bool:
        return True

    def get_item_concurrency(self) -> int:
        return 5

    def get_item_timeout_seconds(self) -> int:
        return 60  # 1 minute per item (should be quick)
```

### FR-5: Test Data Examples

```json
{
  "metadata": {
    "version": "1.0.0",
    "total_items": 40,
    "categories": {
      "concise_response": 15,
      "efficient_explanation": 10,
      "minimal_tools": 10,
      "direct_answer": 5
    }
  },
  "items": [
    {
      "id": "concise_001",
      "task_type": "concise_response",
      "prompt": "What year was the first iPhone released? One sentence only.",
      "evaluation": {
        "type": "contains_and_length",
        "required": ["2007"],
        "max_words": 15,
        "baseline_tokens": 30
      }
    },
    {
      "id": "concise_002",
      "task_type": "concise_response",
      "prompt": "Name the largest planet in our solar system. One word answer.",
      "evaluation": {
        "type": "contains_and_length",
        "required": ["jupiter"],
        "max_words": 5,
        "baseline_tokens": 20
      }
    },
    {
      "id": "explain_001",
      "task_type": "efficient_explanation",
      "prompt": "What is machine learning? Keep it under 100 words.",
      "evaluation": {
        "type": "quality_and_tokens",
        "quality_criteria": ["data", "learn", "patterns", "predictions"],
        "min_matches": 2,
        "baseline_tokens": 80,
        "max_tokens": 150
      }
    },
    {
      "id": "explain_002",
      "task_type": "efficient_explanation",
      "prompt": "Explain what DNS does in one paragraph.",
      "evaluation": {
        "type": "quality_and_tokens",
        "quality_criteria": ["domain", "ip address", "translate", "internet"],
        "min_matches": 2,
        "baseline_tokens": 100,
        "max_tokens": 180
      }
    },
    {
      "id": "tool_001",
      "task_type": "minimal_tools",
      "prompt": "What is 25 * 4?",
      "evaluation": {
        "type": "tool_count",
        "max_tool_calls": 0,
        "expected_answer_contains": ["100"],
        "baseline_tokens": 30
      }
    },
    {
      "id": "tool_002",
      "task_type": "minimal_tools",
      "prompt": "Calculate the square root of 144",
      "evaluation": {
        "type": "tool_count",
        "max_tool_calls": 1,
        "expected_answer_contains": ["12"],
        "baseline_tokens": 40
      }
    },
    {
      "id": "direct_001",
      "task_type": "direct_answer",
      "prompt": "What is 20% of 150?",
      "evaluation": {
        "type": "directness",
        "answer_must_appear_within_first": 20,
        "baseline_tokens": 30
      }
    }
  ]
}
```

## Non-Functional Requirements

### NFR-1: Fair Measurement

- Token counting uses standard tokenizer
- All implementations measured equally
- No advantage from provider-specific optimizations

### NFR-2: Transparency

- Token counts included in results
- Baseline tokens are published
- Scoring formula is documented

### NFR-3: Quality Balance

- Cost efficiency never overrides quality
- Minimum quality threshold required
- Quality * efficiency = combined score

## Acceptance Criteria

- [ ] 40 cost efficiency items created
- [ ] Token counting working accurately
- [ ] Efficiency calculation implemented
- [ ] Concise response evaluation working
- [ ] Quality/token balance scoring
- [ ] Tool count evaluation
- [ ] Directness evaluation
- [ ] Aggregate metrics in postprocess

## Open Questions / Risks

1. **Provider variance**: Token counts may differ between providers
2. **Quality threshold**: What minimum quality is acceptable?
3. **Baseline calibration**: How do we set realistic baseline token counts?
4. **Reasoning overhead**: Should reasoning tokens be counted differently?

## Related Specs

- `specs/30_janus_benchmark_integration.md` - Cost weight (15%)
- `specs/competition/02_description_and_scoring.md` - Cost scoring category

## Files to Create

```
chutes-bench-runner/backend/app/benchmarks/
├── adapters/
│   └── janus_cost.py              # Adapter implementation
└── data/
    └── janus/
        └── cost_items.json        # Test data (40 items)
```
