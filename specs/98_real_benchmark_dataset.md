# Spec 98: Real Benchmark Dataset

## Status: COMPLETE

## Context / Why

For the miner competition to be fair and meaningful, we need a proper evaluation dataset with:
- Public train/dev sets for miners to optimize against
- Private test set to prevent overfitting
- Diverse coverage across all Janus capabilities
- Automated evaluation pipeline

Currently we have benchmark stubs but no real dataset.

## Goals

- Create comprehensive benchmark dataset covering all Janus use cases
- Separate public (train/dev) and private (test) sets
- Ensure anti-overfitting measures
- Enable automated scoring

## Dataset Categories

### 1. General Chat (20% of dataset)

Simple conversational queries that should use the fast path.

```json
{
  "id": "chat_001",
  "category": "chat",
  "input": {
    "messages": [{"role": "user", "content": "What is the capital of France?"}]
  },
  "expected": {
    "type": "text",
    "contains": ["Paris"],
    "max_latency_ms": 2000
  }
}
```

### 2. Research / Web Search (20% of dataset)

Queries requiring current information from the web.

```json
{
  "id": "research_001",
  "category": "research",
  "input": {
    "messages": [{"role": "user", "content": "What were the major AI announcements at CES 2026?"}]
  },
  "expected": {
    "type": "text",
    "requires_citations": true,
    "min_sources": 2,
    "recency_required": true
  }
}
```

### 3. Code Generation (20% of dataset)

Programming tasks from simple to complex.

```json
{
  "id": "code_001",
  "category": "code",
  "input": {
    "messages": [{"role": "user", "content": "Write a Python function to check if a number is prime"}]
  },
  "expected": {
    "type": "code",
    "language": "python",
    "must_execute": true,
    "test_cases": [
      {"input": [2], "output": true},
      {"input": [4], "output": false},
      {"input": [17], "output": true}
    ]
  }
}
```

### 4. Multimodal (15% of dataset)

Image understanding, generation, audio.

```json
{
  "id": "multimodal_001",
  "category": "multimodal",
  "subcategory": "vision",
  "input": {
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What animal is in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }]
  },
  "expected": {
    "type": "text",
    "contains": ["cat"]
  }
}
```

### 5. Tool Use / Agentic (15% of dataset)

Complex tasks requiring tool orchestration.

```json
{
  "id": "agentic_001",
  "category": "agentic",
  "input": {
    "messages": [{"role": "user", "content": "Download the README from https://github.com/anthropics/claude-code and summarize it"}]
  },
  "expected": {
    "type": "text",
    "requires_tool_use": true,
    "tools_expected": ["web_fetch", "file_read"],
    "min_length": 200
  }
}
```

### 6. Long-Form / Deep Research (10% of dataset)

Extended research tasks.

```json
{
  "id": "deep_001",
  "category": "deep_research",
  "input": {
    "messages": [{"role": "user", "content": "Write a comprehensive analysis of the pros and cons of Rust vs Go for backend development"}]
  },
  "expected": {
    "type": "text",
    "min_length": 1500,
    "must_cover": ["performance", "safety", "ecosystem", "learning curve"],
    "max_time_seconds": 120
  }
}
```

## Dataset Structure

```
bench/
├── datasets/
│   ├── public/
│   │   ├── train/
│   │   │   ├── chat.jsonl
│   │   │   ├── research.jsonl
│   │   │   ├── code.jsonl
│   │   │   ├── multimodal.jsonl
│   │   │   ├── agentic.jsonl
│   │   │   └── deep_research.jsonl
│   │   └── dev/
│   │       └── ... (same structure, smaller)
│   └── private/
│       └── test/
│           └── ... (not in git, loaded from secure storage)
├── evaluators/
│   ├── text_evaluator.py
│   ├── code_evaluator.py
│   ├── citation_evaluator.py
│   └── multimodal_evaluator.py
└── runner.py
```

## Evaluation Metrics

### Per-Category Metrics

| Category | Primary Metric | Secondary Metrics |
|----------|---------------|-------------------|
| Chat | Accuracy | Latency, coherence |
| Research | Citation quality | Recency, coverage |
| Code | Test pass rate | Syntax validity, efficiency |
| Multimodal | Accuracy | Latency |
| Agentic | Task completion | Tool efficiency, errors |
| Deep Research | Coverage score | Length, structure |

### Aggregate Scoring

```python
def compute_composite_score(results: dict) -> float:
    weights = {
        "chat": 0.15,
        "research": 0.20,
        "code": 0.20,
        "multimodal": 0.15,
        "agentic": 0.20,
        "deep_research": 0.10,
    }

    score = 0.0
    for category, weight in weights.items():
        category_score = results[category]["score"]
        score += weight * category_score

    # Apply cost penalty
    cost_factor = 1.0 - (results["total_cost"] / MAX_EXPECTED_COST) * 0.1

    # Apply latency penalty
    latency_factor = 1.0 - (results["avg_latency"] / MAX_EXPECTED_LATENCY) * 0.1

    return score * cost_factor * latency_factor
```

## Anti-Overfitting Measures

1. **Private Test Set**: Never published, rotated periodically
2. **Dynamic Questions**: Some questions generated at eval time
3. **Paraphrasing**: Same questions asked differently
4. **Temporal Freshness**: Research questions about recent events
5. **Rate Limiting**: Max evals per day per submission

## Acceptance Criteria

- [ ] 100+ questions in public train set
- [ ] 50+ questions in public dev set
- [ ] Private test set created and secured
- [ ] All 6 categories covered
- [ ] Evaluators implemented for each type
- [ ] Automated scoring pipeline working
- [ ] Leaderboard updates from benchmark runs

## Files to Create

```
bench/
├── datasets/
│   └── public/
│       ├── train/*.jsonl
│       └── dev/*.jsonl
├── evaluators/
│   ├── base.py
│   ├── text_evaluator.py
│   ├── code_evaluator.py
│   ├── citation_evaluator.py
│   └── multimodal_evaluator.py
├── scoring.py
└── runner.py  # MODIFY: Use new dataset/evaluators
```

## Related Specs

- Spec 12: Benchmarking Scoring
- Spec 30-35: Janus Benchmarks
- Spec 56: Scoring Service Backend

NR_OF_TRIES: 1
