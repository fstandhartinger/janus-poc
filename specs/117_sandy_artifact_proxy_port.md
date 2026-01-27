# 117 Sandy artifact proxy port alignment

## Status: COMPLETE

## Problem
Sandy sandbox public URLs only proxy the sandbox runtime port (default 5173). Our artifact server was binding to port 8787, so artifact URLs like
`https://<sandbox>.sandy.../artifacts/<file>` returned 404/partial content. The UI cache route attempted to fetch those URLs and stored broken images.

## Goals
- Artifact URLs served from the sandbox public URL must return full bytes reliably.
- Eliminate base64 image blobs from agent stdout (avoid truncation).
- Keep the caching pipeline unchanged: UI downloads artifacts from sandbox URL, stores in `/var/data`, serves from `/api/artifacts/...`.

## Non-Goals
- No new persistence layer (keep `/var/data` cache for now).
- No changes to Sandy proxy behavior.

## Desired Approach
1. **Bind artifact server to Sandy runtime port**
   - Use `JANUS_ARTIFACT_PORT=5173` (or `SANDY_RUNTIME_PORT`) inside the sandbox.
   - Ensure the artifact HTTP server listens on the same port Sandy proxies.

2. **Keep artifact URLs stable**
   - `JANUS_ARTIFACT_URL_BASE` stays as `{sandbox_url}/artifacts`.
   - UI caching route downloads artifacts from those URLs before termination.

3. **Update prompts and docs**
   - System prompts and README should state the runtime port requirement.
   - Remove any instructions that embed base64 data URLs for images.

4. **Grace period remains**
   - Keep sandbox alive briefly after emitting artifacts to allow downloads.

## Implementation Checklist
- [ ] Default `JANUS_ARTIFACT_PORT` to 5173 in baseline-agent-cli settings.
- [ ] Update bootstrap artifact server default to 5173.
- [ ] Update agent prompts/docs to reference runtime port (5173).
- [ ] Verify artifact URLs load via public sandbox URL.
- [ ] Update history and mark COMPLETE.

## Test Plan
- Trigger "create an image of a cute cat" via UI.
  - Expect `artifacts` SSE event.
  - Expect UI to cache and render image from `/api/artifacts/...`.
- Repeat 5-10 times; success rate should be 100%.
- Verify artifact URL (sandbox) returns HTTP 200 before termination.

## Rollout
- Deploy baseline-agent-cli changes.
- Validate in production UI via Playwright.
