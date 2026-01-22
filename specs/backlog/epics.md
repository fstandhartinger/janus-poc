# Janus PoC Epics

## Epic 1: Gateway Core
- Implement OpenAI-compatible `/v1/chat/completions`.
- Add competitor registry and routing.
- SSE streaming pass-through and keep-alives.

## Epic 2: Chat UI
- Next.js UI with sessions, streaming, markdown, attachments.
- Thinking panel for reasoning_content.
- Artifact rendering and downloads.

## Epic 3: Baseline Competitor
- Fast-path chat.
- Sandy-based CLI agent path.
- Artifact generation and usage reporting.

## Epic 4: Benchmark Runner
- Public train/dev suites and runner CLI.
- Composite scoring and streaming metrics.
- Results export (JSON + markdown summary).

## Epic 5: Guardrails + Platform Services
- Egress allowlist and proxy stubs.
- Sandbox resource limits and timeouts.
- Artifact access controls.

## Epic 6: Ops + Observability
- Structured logs and health endpoints.
- Basic metrics for latency and streaming gaps.
- Developer automation scripts.

## Epic 7: Phase 2 Marketplace (Spec-only)
- Component registry contracts.
- Attribution and reward split model.
