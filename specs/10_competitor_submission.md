# Competitor Submission Interface

## Status: COMPLETE

## Context / Why
Miners/competitors must submit containers that expose a stable, OpenAI-compatible API.
This document defines the required endpoints, behavior, and guardrails for submissions.

## Goals
- Provide a clear contract for competitor containers.
- Keep the API OpenAI-compatible and easy to test.
- Ensure streaming and artifact outputs are supported.

## Non-goals
- A full submission marketplace or review pipeline.
- Mandatory use of any specific agent framework (n8n, squad, etc.).

## Functional requirements
- Expose **required endpoints**:
  - `POST /v1/chat/completions`
  - `GET /health`
- Expose **optional endpoints**:
  - `GET /metrics` (Prometheus-style or JSON)
  - `GET /debug` (local-only; disabled in production)
- Support `stream: true` with continuous SSE updates.
- Emit `reasoning_content` or Janus streaming extensions.
- Return artifact descriptors for non-text outputs.
- Report minimal usage and cost estimates.

## Non-functional requirements
- Must start and be ready within 30 seconds.
- Must handle at least 2 concurrent requests.
- Must respect request timeouts (default **5 minutes**, configurable via gateway).
- Must keep the SSE connection alive with frequent updates or keep-alive comments.

## API/contracts
- OpenAI-compatible schema as defined in `specs/04_openai_api_compat.md`.
- Streaming contract as defined in `specs/05_streaming_contract.md`.
- Artifact schema as defined in `specs/06_artifacts_and_files.md`.

## Submission packaging
- Container exposes HTTP on port `8080` by default.
- Container must accept configuration via environment variables.
- No outbound internet access except platform proxies.
- Artifact URLs must be resolvable to sandbox-hosted files or `data:` URLs.
 - If using sandbox-hosted artifacts, competitors should expose them on a fixed port/path.

## Cost accounting (minimal)
Each response should include a `usage` object with:
- `prompt_tokens`, `completion_tokens`, `total_tokens`
- Optional `cost_usd` (estimated), `sandbox_seconds`

## Acceptance criteria
- A competitor container can be health-checked and passes a basic chat request.
- Streaming output includes continuous `reasoning_content` updates.
- Artifacts can be retrieved via sandbox URL or base64 `data:` URL and are verifiable by hash.

## Open questions / risks
- Should we require a `/v1/models` endpoint for competitor discovery?
- What is the minimum acceptable concurrency for PoC?
