# Janus PoC Tickets

## Gateway
- Implement FastAPI project scaffold with pydantic settings and env loading.
- Add `/v1/chat/completions` request validation and routing.
- Implement SSE pass-through with keep-alive pings.
- Add competitor registry (YAML or JSON config) and selection logic.
- Implement artifact proxy endpoint `/v1/artifacts/{id}`.

## UI
- Create Next.js app with sidebar + chat layout.
- Add markdown rendering (`react-markdown`, `remark-gfm`).
- Implement streaming client (SSE) with incremental rendering.
- Add image upload and inline `image_url` content parts.
- Add reasoning panel toggle.

## Baseline Competitor
- Implement `/health` and `/v1/chat/completions`.
- Add fast-path (direct LLM call).
- Add Sandy integration for CLI agent path.
- Collect artifacts and return descriptors.
- Emit `reasoning_content` and tool events in stream.

## Benchmark Runner
- Define dataset schema and directory layout.
- Implement runner CLI with deterministic subsets.
- Add scoring for quality, speed, cost, streaming, multimodal.
- Generate JSON summary reports.

## Guardrails
- Stub platform proxy endpoints (web/search/vector).
- Enforce no-external-egress policy (documented or stubbed).
- Add request timeouts and size limits.

## Ops
- Add `/health` and `/metrics` endpoints.
- Add structured logging (request id, competitor id, latency).
- Add automation scripts for /autonomous, /test-all, /visual-test, /verify-complete.
