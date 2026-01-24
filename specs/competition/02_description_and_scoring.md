# Spec: Description Copy & Scoring Model

## Status: COMPLETE

## Context / Why

The current competition description is too narrowly focused on "agents" and doesn't fully convey the breadth of what Janus evaluates. The scoring model mentions quality, speed, and cost, but the actual evaluation will cover a much wider range of capabilities and metrics.

Users need to understand that:
1. They submit an **OpenAI-compatible API endpoint**, not "an agent"
2. The evaluation covers **all use cases** of a comprehensive AI assistant
3. Scoring includes both **functional metrics** (task performance) and **non-functional metrics** (speed, cost, streaming)

## Goals

- Rewrite the introductory description to frame submissions as **intelligence implementations**
- Clearly explain the breadth of evaluation categories
- Present the scoring model in a way that's understandable but flexible for future expansion
- Avoid hard-coding specific weights (the formula will evolve)

## Non-Goals

- Defining the exact benchmark suite (will be determined separately)
- Implementing the scoring algorithm
- Designing the leaderboard UI (separate spec)

## Functional Requirements

### FR-1: Introductory Description

**Current copy (paraphrased):**
> Miners compete by submitting an OpenAI-compatible AI agent that handles chat, reasoning, research, code generation, and more. Score is based on quality, speed, and cost.

**New copy:**

```markdown
## What is the Janus Competition?

The Janus Competition is an open arena where developers compete to build
the **best intelligence engine** — a system that handles any request a user
might throw at a comprehensive AI assistant.

### How It Works

You submit an **OpenAI-compatible API endpoint**. Behind that endpoint, your
implementation can use any technology: CLI agents, workflow engines, model
routers, multi-agent orchestrations, or entirely novel approaches. As long as
it speaks the OpenAI Chat Completions API and streams responses, you're in.

### What Gets Evaluated

Your implementation is scored across **all the use cases** of a modern AI assistant:

- **Simple chat**: Conversational responses, Q&A, summarization
- **Complex reasoning**: Multi-step problems, logical deduction, planning
- **Deep research**: Web search, information synthesis, citation
- **Software creation**: Code generation, debugging, full project scaffolding
- **Multimodal input**: Understanding images, documents, audio
- **Multimodal output**: Generating images, files, structured data
- **Tool use**: Calling APIs, executing code, managing files

And across **non-functional metrics** that matter in production:

- **Quality**: Accuracy, helpfulness, safety, instruction following
- **Speed**: Time to first token, total completion time
- **Cost**: Resource efficiency, inference cost per request
- **Streaming continuity**: Consistent token flow, reasoning transparency
- **Modality handling**: Graceful handling of images, files, multi-turn context

The composite score reflects how well your implementation performs as a
**complete AI solution**, not just on narrow benchmarks.
```

### FR-2: Scoring Categories Table

Display a clear breakdown of evaluation categories:

```markdown
## Scoring Categories

| Category | What It Measures | Example Benchmarks |
|----------|------------------|-------------------|
| **Chat Quality** | Conversational ability, helpfulness | MT-Bench, AlpacaEval |
| **Reasoning** | Logic, math, multi-step problems | GSM8K, MATH, ARC |
| **Knowledge** | Factual accuracy, world knowledge | MMLU, TruthfulQA |
| **Research** | Web search, synthesis, citation | Custom research tasks |
| **Coding** | Code generation, debugging, explanation | HumanEval, MBPP, SWE-Bench |
| **Tool Use** | API calling, function execution | Custom tool-use evals |
| **Multimodal** | Image understanding, file generation | VQA, document tasks |
| **Speed** | Latency, tokens per second | Time-to-first-token, TPS |
| **Cost** | Resource efficiency | USD per 1M tokens (effective) |
| **Streaming** | Continuous output, reasoning tokens | Streaming continuity score |
```

### FR-3: Composite Score Formula

Present the formula conceptually without hard-coding weights:

```markdown
## Composite Score

The final leaderboard ranking is based on a **composite score** that combines
all evaluation categories. The formula is designed to reward implementations
that excel across the board, not just in one area.

**Conceptual formula:**

```
CompositeScore = Σ (CategoryScore × CategoryWeight)
```

Where:
- Each category is scored on a normalized scale (0-100)
- Weights reflect the importance of each category to real-world usage
- Weights are published and may be adjusted as the competition evolves

**Current weight distribution** (subject to change):

| Category | Weight |
|----------|--------|
| Quality (aggregate) | 40% |
| Speed | 20% |
| Cost | 15% |
| Streaming | 15% |
| Modality | 10% |

*Note: Quality aggregate includes chat, reasoning, knowledge, research, coding,
tool use, and multimodal task performance.*

We will publish the exact formula and weights before each evaluation cycle.
The goal is a transparent, reproducible scoring system.
```

### FR-4: Leaderboard Columns

The leaderboard table should display:

| Column | Description |
|--------|-------------|
| Rank | Current position |
| Implementation | Name/identifier of the submission |
| Miner | Bittensor hotkey (truncated) |
| Composite | Overall score (0-100) |
| Quality | Aggregate task performance |
| Speed | Latency score |
| Cost | Efficiency score |
| Streaming | Continuity score |
| Modality | Multi-modal handling |
| Submitted | Date of submission |
| Days at #1 | (For top entry) How long at top |

### FR-5: Public Benchmark Reference

Mention that evaluations use established public benchmarks:

```markdown
## Benchmark Suites

Evaluations use a combination of public and proprietary benchmarks:

**Public benchmarks** (reproducible):
- MMLU (knowledge)
- TruthfulQA (accuracy)
- GSM8K, MATH (reasoning)
- HumanEval, MBPP (coding)
- MT-Bench (chat quality)

**Proprietary benchmarks** (Janus-specific):
- Research synthesis tasks
- Multi-step tool use scenarios
- Streaming continuity tests
- Multimodal generation tasks

All public benchmark implementations are open source. Proprietary benchmarks
are designed to prevent overfitting and will be rotated periodically.
```

## Non-Functional Requirements

### NFR-1: Clarity

- Use plain language; avoid jargon where possible
- Provide examples for each evaluation category
- Make it clear what "good" looks like

### NFR-2: Flexibility

- The scoring model will evolve; avoid language that implies it's fixed
- Use "current" or "initial" when describing weights
- Note that weights will be published before each cycle

### NFR-3: Transparency

- Emphasise that scoring is transparent and reproducible
- Mention that benchmark code is open source
- Explain how disputes or questions are handled

## Acceptance Criteria

- [ ] Introductory copy explains submissions as "OpenAI-compatible API endpoints"
- [ ] Copy lists all use case categories (chat, reasoning, research, coding, tool use, multimodal)
- [ ] Copy lists all non-functional metrics (quality, speed, cost, streaming, modality)
- [ ] Scoring categories table is present with example benchmarks
- [ ] Composite score formula is explained conceptually
- [ ] Weights are presented as "current" and subject to change
- [ ] Leaderboard column definitions are documented
- [ ] Public benchmark suites are named (MMLU, HumanEval, etc.)
- [ ] No hard-coded weights that imply permanence

## Open Questions / Risks

1. **Weight calibration**: How do we determine initial weights? Need community input or data-driven approach.
2. **Benchmark gaming**: If benchmarks are public, submissions may overfit. Mitigation: proprietary test sets, rotation.
3. **Category expansion**: How do we add new categories (e.g., "agentic browsing") without disrupting rankings?

## Related Specs

- `01_competition_overview.md` – Naming and framing
- `03_steps_and_prize_pool.md` – Process steps and prize mechanism
