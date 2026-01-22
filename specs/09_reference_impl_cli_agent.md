# Reference Implementation: CLI Agent Baseline

## Context / Why
The baseline competitor sets the minimum bar for miners. It must be strong enough to
handle simple chat tasks quickly and complex tasks via a CLI agent inside Sandy.

## Goals
- Provide a competitive, reproducible baseline.
- Demonstrate tool use, artifacts, and streaming reasoning.
- Keep the implementation aligned with existing Chutes tooling.

## Non-goals
- A state-of-the-art autonomous agent or multi-agent system.
- Support for proprietary closed-source agent frameworks only.

## Functional requirements
- Expose `/v1/chat/completions` and `/health`.
- Implement a **fast path** for short, simple prompts (no sandbox).
- Implement a **complex path** that:
  1) Creates a Sandy sandbox.
  2) Runs a CLI agent with an "agent pack".
  3) Collects outputs and artifacts.
- Stream intermediate steps via `reasoning_content`.
- Generate artifact descriptors for files produced in the sandbox.

## Non-functional requirements
- Sandbox runs should be bounded by a configurable timeout.
- The baseline should be deterministic enough for scoring in benchmarks.

## API/contracts
- OpenAI-compatible request/response with Janus extensions.
- Uses platform services for web search, vector search, and model calls.

## Baseline agent selection
- **Default agent**: OpenHands CLI (open source, configurable).
- **Fallback**: OpenCode or Aider CLI if OpenHands is unavailable.
- **Config**: Agent choice set via `JANUS_BASELINE_AGENT` env var.

## Agent pack concept
- A versioned directory containing:
  - system prompt
  - tool definitions (MCP or CLI wrappers)
  - sandbox bootstrap scripts
  - model config (Chutes model IDs)
- The agent pack is mounted or copied into the Sandy sandbox before execution.

## Data flow
```mermaid
flowchart LR
  REQ[Chat Request] --> DECIDE{Fast or Complex?}
  DECIDE -->|Fast| LLM[Direct LLM Call]
  DECIDE -->|Complex| SANDY[Sandy Sandbox]
  SANDY --> AGENT[CLI Agent]
  AGENT --> ART[Artifacts + Output]
  LLM --> OUT[Response]
  ART --> OUT
```

## Acceptance criteria
- The baseline responds to a simple prompt in < 3s without Sandy usage.
- The baseline can run a CLI agent in Sandy and return a file artifact.
- Streaming includes sandbox lifecycle steps and tool outputs.

## Open questions / risks
- Which CLI agent is most stable in Sandy for PoC (OpenHands vs OpenCode)?
- How to detect "complex" prompts reliably without adding latency?
