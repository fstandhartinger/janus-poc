# Janus PoC Overview

## Context / Why
Janus is a competitive, OpenAI-compatible intelligence API where miners submit arbitrary
containers that expose `/v1/chat/completions` and stream continuously. We need a PoC that
proves the end-to-end flow: a ChatGPT-like UI, a gateway that runs/chooses competitor
containers, a strong baseline reference implementation, and a minimal evaluation harness.

This PoC must reuse existing Chutes conventions:
- **Sandy** for sandboxed execution (treat as TEE-like isolation for architecture).
- **chutes-knowledge-agent** for UI and agent app patterns.
- **chutes-bench-runner** for evaluation runner patterns and scoring flow.
- **affine/memory.md** for additional conventions and context (if applicable).

## Goals
- Define an implementation-grade spec suite for the Janus PoC.
- Preserve OpenAI Chat Completions compatibility with streaming and reasoning traces.
- Provide a baseline competitor that uses a CLI agent in Sandy.
- Provide a minimal, reproducible benchmarking harness with a composite score.
- Specify guardrails and platform services for controlled egress.

## Non-goals
- Production TEE deployment or attestation.
- Full marketplace implementation (Phase 2 only).
- Full multi-tenant auth and billing.
- Complete benchmark coverage or large public datasets.

## Functional requirements
- A minimal ChatGPT-like UI with sessions, streaming, markdown rendering, and attachments.
- A Janus Gateway that selects and runs competitor containers and proxies streaming.
- A baseline competitor container that demonstrates tool use and artifact outputs.
- A competitor contract for OpenAI-compatible streaming responses and health checks.
- A benchmark harness with public train/dev and private test stubs.
- Explicit guardrails for egress and sandbox usage.

## Non-functional requirements
- **Streaming:** time-to-first-token < 2s in local dev; max gap < 2s (keep-alives allowed).
- **Latency:** P50 end-to-end response < 8s for short prompts in baseline mode.
- **Reliability:** gateway must handle competitor failures with clear error surfaces.
- **Security:** no direct external egress without platform proxy; sandboxed tool execution.
- **Cost accounting:** minimal usage reporting per request.

## API/contracts
- OpenAI Chat Completions compatibility: `specs/04_openai_api_compat.md`
- Streaming contract: `specs/05_streaming_contract.md`
- Artifacts and retrieval: `specs/06_artifacts_and_files.md`
- Competitor submission interface: `specs/10_competitor_submission.md`
- OpenAPI docs: `specs/openapi/`

## Data flow
```mermaid
flowchart LR
  UI[Chat UI] -->|/v1/chat/completions (stream)| GW[Janus Gateway]
  GW -->|OpenAI-compatible request| COMP[Competitor Container]
  COMP -->|SSE stream + artifacts| GW
  COMP -->|Tool calls| SVC[Platform Services]
  COMP -->|CLI agent| SANDY[Sandy Sandbox]
  GW -->|SSE stream| UI
  GW -->|artifact proxy| UI
```

## Acceptance criteria
- All required spec files are present and follow the mandated structure.
- Specs explicitly reuse Sandy, chutes-knowledge-agent, and chutes-bench-runner patterns.
- OpenAPI specs exist for OpenAI compatibility and competitor extensions.
- At least three Mermaid diagrams are included across the spec suite.

## Open questions / risks
- How strict should the streaming continuity requirement be for slow tools?
- How much of the guardrail enforcement should be in the gateway vs competitor container?
