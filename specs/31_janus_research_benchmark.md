# Spec 31: Janus Research Benchmark

## Status: DRAFT

## Context / Why

A key differentiator for Janus intelligence implementations is the ability to perform real-time research — searching the web, fetching pages, synthesizing information, and verifying facts. This is fundamentally different from static knowledge benchmarks like MMLU or TruthfulQA.

The Janus Research Benchmark evaluates an implementation's ability to:
1. **Search** - Use web search APIs effectively
2. **Fetch** - Retrieve and parse web content
3. **Synthesize** - Combine multiple sources into coherent answers
4. **Verify** - Cross-check facts across sources
5. **Cite** - Provide proper attribution

## Goals

- Measure research capabilities that require real-time web access
- Evaluate quality of synthesis from multiple sources
- Test fact verification and currency of information
- Assess proper citation and source attribution
- Provide reproducible scores for competition ranking

## Non-Goals

- Testing static knowledge (covered by MMLU, TruthfulQA)
- Testing reasoning without web access (covered by GSM8K, GPQA)
- Testing coding abilities (covered by HumanEval, LiveCodeBench)

## Functional Requirements

### FR-1: Task Types

The benchmark includes five task types:

#### 1. Fact Verification (20 items)

Verify claims that require current information:

```json
{
  "id": "fact_001",
  "task_type": "fact_verification",
  "claim": "The current CEO of OpenAI is Sam Altman",
  "evaluation": {
    "type": "boolean_with_evidence",
    "requires": ["search_performed", "source_cited", "correct_conclusion"]
  }
}
```

#### 2. Current Events (20 items)

Questions about recent events:

```json
{
  "id": "current_001",
  "task_type": "current_events",
  "query": "What were the main announcements at the most recent Apple WWDC?",
  "evaluation": {
    "type": "key_facts",
    "expected_topics": ["ios", "macos", "hardware", "ai_features"],
    "min_topics": 3
  }
}
```

#### 3. Comparative Research (20 items)

Compare and contrast topics requiring multiple sources:

```json
{
  "id": "compare_001",
  "task_type": "comparative",
  "query": "Compare the AI regulation approaches of the EU and China",
  "evaluation": {
    "type": "balanced_comparison",
    "required_aspects": ["eu_ai_act", "china_approach", "key_differences", "similarities"],
    "min_sources": 2
  }
}
```

#### 4. Synthesis (20 items)

Synthesize information from multiple sources:

```json
{
  "id": "synthesis_001",
  "task_type": "synthesis",
  "query": "What are the current best practices for fine-tuning large language models?",
  "evaluation": {
    "type": "comprehensive_answer",
    "required_elements": ["lora", "qlora", "full_finetuning", "dataset_prep"],
    "quality_criteria": ["technical_accuracy", "practical_advice", "source_diversity"]
  }
}
```

#### 5. Deep Dive (20 items)

In-depth research on specific topics:

```json
{
  "id": "deep_001",
  "task_type": "deep_dive",
  "query": "Explain how Bittensor's incentive mechanism works, including the role of validators and miners",
  "evaluation": {
    "type": "expert_level",
    "required_concepts": ["subnet", "validator", "miner", "emission", "consensus"],
    "depth_indicators": ["technical_details", "examples", "tradeoffs"]
  }
}
```

### FR-2: Evaluation Methods

#### LLM Judge Evaluation

Use a judge model to evaluate response quality:

```python
JUDGE_PROMPT = """
You are evaluating a research response for quality and accuracy.

Task: {task_description}
Query: {query}
Response: {response}

Evaluate on these criteria (0-1 scale each):
1. Factual Accuracy: Are the facts correct and verifiable?
2. Source Quality: Were reliable sources used?
3. Completeness: Does the response fully address the query?
4. Synthesis: Is information from multiple sources well-integrated?
5. Citation: Are sources properly attributed?

Output JSON:
{
  "factual_accuracy": 0.0-1.0,
  "source_quality": 0.0-1.0,
  "completeness": 0.0-1.0,
  "synthesis": 0.0-1.0,
  "citation": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "reasoning": "..."
}
"""
```

#### Key Fact Matching

For current events and fact verification:

```python
def evaluate_key_facts(response: str, expected_facts: list[str]) -> float:
    """Check if response contains expected key facts."""
    found = 0
    for fact in expected_facts:
        if fact.lower() in response.lower():
            found += 1
    return found / len(expected_facts)
```

### FR-3: Adapter Implementation

```python
# backend/app/benchmarks/adapters/janus_research.py

from typing import AsyncIterator
import json
from pathlib import Path

from app.benchmarks.base import BenchmarkAdapter, ItemResult
from app.benchmarks.registry import register_adapter
from app.services.inference_client import InferenceClient


@register_adapter("janus_research")
class JanusResearchAdapter(BenchmarkAdapter):
    """Benchmark for web research and synthesis capabilities."""

    def __init__(
        self,
        client: InferenceClient,
        model_slug: str,
        judge_client: InferenceClient | None = None,
    ):
        super().__init__(client, model_slug, judge_client)
        self._items: list[dict] = []
        self._judge_model = "gpt-4o"  # High-quality judge

    def get_name(self) -> str:
        return "janus_research"

    def get_display_name(self) -> str:
        return "Janus Research"

    def get_category(self) -> str:
        return "Janus Intelligence"

    async def get_total_items(self) -> int:
        if not self._items:
            await self.preload()
        return len(self._items)

    async def preload(self) -> None:
        """Load test items from JSON file."""
        data_path = Path(__file__).parent.parent / "data" / "janus" / "research_items.json"
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
        """Evaluate a single research task."""
        # Find item
        item = next((i for i in self._items if i["id"] == item_id), None)
        if not item:
            return ItemResult(
                item_id=item_id,
                error=f"Item {item_id} not found"
            )

        # Build prompt
        system_prompt = """You are a research assistant with access to web search.
Use your search capabilities to find accurate, up-to-date information.
Always cite your sources."""

        user_prompt = item.get("query") or item.get("claim", "")

        # Get response from target implementation
        try:
            start_time = time.time()
            response = await self.client.chat_completion(
                model=self.model_slug,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            response_text = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens if response.usage else None
            output_tokens = response.usage.completion_tokens if response.usage else None

        except Exception as e:
            return ItemResult(
                item_id=item_id,
                prompt=user_prompt,
                error=str(e)
            )

        # Evaluate response using judge
        score, judge_output = await self._evaluate_with_judge(
            item=item,
            response=response_text
        )

        return ItemResult(
            item_id=item_id,
            item_hash=self.compute_item_hash(item),
            prompt=user_prompt,
            response=response_text,
            is_correct=score >= 0.7,
            score=score,
            judge_output=judge_output,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def _evaluate_with_judge(
        self,
        item: dict,
        response: str
    ) -> tuple[float, dict]:
        """Use judge model to evaluate response quality."""
        judge_prompt = f"""
You are evaluating a research response.

Task Type: {item.get("task_type")}
Query: {item.get("query") or item.get("claim")}

Response to evaluate:
{response}

Evaluation criteria:
{json.dumps(item.get("evaluation", {}), indent=2)}

Score the response 0.0-1.0 and explain your reasoning.
Output JSON with "score" and "reasoning" fields.
"""

        try:
            judge_response = await self.judge_client.chat_completion(
                model=self._judge_model,
                messages=[{"role": "user", "content": judge_prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            result = json.loads(judge_response.choices[0].message.content)
            return result.get("score", 0.0), result

        except Exception as e:
            return 0.0, {"error": str(e)}

    def supports_parallel_items(self) -> bool:
        return True

    def get_item_concurrency(self) -> int:
        return 3  # Limit concurrent requests

    def get_item_timeout_seconds(self) -> int:
        return 300  # 5 minutes per item (research takes time)
```

### FR-4: Test Data Generation

Create diverse, high-quality test items:

```python
# scripts/generate_research_items.py

import json
from datetime import datetime

RESEARCH_ITEMS = {
    "metadata": {
        "version": "1.0.0",
        "created": datetime.now().isoformat(),
        "total_items": 100,
        "categories": {
            "fact_verification": 20,
            "current_events": 20,
            "comparative": 20,
            "synthesis": 20,
            "deep_dive": 20
        }
    },
    "items": [
        # Fact verification items
        {
            "id": "fact_001",
            "task_type": "fact_verification",
            "claim": "Tesla delivered over 1 million vehicles in 2023",
            "evaluation": {
                "type": "boolean_with_evidence",
                "requires_search": True
            }
        },
        # ... more items
    ]
}

if __name__ == "__main__":
    with open("backend/app/benchmarks/data/janus/research_items.json", "w") as f:
        json.dump(RESEARCH_ITEMS, f, indent=2)
```

### FR-5: Metrics Collection

Track research-specific metrics:

```python
async def postprocess(self, results: list[ItemResult]) -> dict:
    """Compute aggregate research metrics."""
    metrics = {
        "by_task_type": {},
        "avg_latency_ms": 0,
        "search_usage_rate": 0,
        "citation_rate": 0,
    }

    task_type_scores = {}
    total_latency = 0
    search_count = 0
    citation_count = 0

    for result in results:
        if result.error:
            continue

        # Group by task type
        item = next((i for i in self._items if i["id"] == result.item_id), None)
        if item:
            task_type = item.get("task_type", "unknown")
            if task_type not in task_type_scores:
                task_type_scores[task_type] = []
            task_type_scores[task_type].append(result.score or 0)

        # Latency
        if result.latency_ms:
            total_latency += result.latency_ms

        # Check for search usage (heuristic)
        if result.response and any(
            indicator in result.response.lower()
            for indicator in ["according to", "source:", "found that", "search results"]
        ):
            search_count += 1

        # Check for citations
        if result.response and any(
            indicator in result.response
            for indicator in ["http", "www.", "[source]", "[1]", "[2]"]
        ):
            citation_count += 1

    # Aggregate
    for task_type, scores in task_type_scores.items():
        metrics["by_task_type"][task_type] = {
            "count": len(scores),
            "avg_score": sum(scores) / len(scores) if scores else 0
        }

    valid_results = [r for r in results if not r.error]
    if valid_results:
        metrics["avg_latency_ms"] = total_latency / len(valid_results)
        metrics["search_usage_rate"] = search_count / len(valid_results)
        metrics["citation_rate"] = citation_count / len(valid_results)

    return metrics
```

## Non-Functional Requirements

### NFR-1: Reproducibility

- Same seed produces same item subset
- Judge evaluations are deterministic (temperature=0)
- Test items are versioned

### NFR-2: Fairness

- All implementations have equal access to platform services
- No advantage from pre-cached data
- Rate limits are uniform

### NFR-3: Freshness

- Some items require information from the last 30 days
- Items are updated quarterly to prevent memorization
- Clearly mark items with recency requirements

## Acceptance Criteria

- [ ] 100 research items created and validated
- [ ] 5 task types with 20 items each
- [ ] LLM judge evaluation working
- [ ] Latency tracking per item
- [ ] Search and citation rate metrics
- [ ] Task type breakdown in results
- [ ] Subset sampling with deterministic seeding
- [ ] Integration tests passing

## Open Questions / Risks

1. **Judge reliability**: How consistent is the LLM judge? Need inter-rater reliability testing.
2. **Recency requirements**: How do we ensure implementations have access to recent information?
3. **Search API availability**: What if search.janus.rodeo is down during evaluation?
4. **Language**: All items in English; future spec for multilingual support?

## Related Specs

- `specs/30_janus_benchmark_integration.md` - Overview and scoring weights
- `specs/competition/02_description_and_scoring.md` - Quality scoring category
- `specs/competition/05_architecture_overview.md` - Platform services (search, proxy)

## Files to Create

```
chutes-bench-runner/backend/app/benchmarks/
├── adapters/
│   └── janus_research.py          # Adapter implementation
└── data/
    └── janus/
        └── research_items.json    # Test data (100 items)
```
