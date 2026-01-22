# Artifacts and File Handling

## Context / Why
Janus supports "anything out" outputs, but the MVP will surface non-text outputs as
artifact descriptors and retrieval URLs. This document defines the artifact schema and
how uploads/downloads work.

## Goals
- Define an artifact descriptor schema.
- Specify how artifact URLs are exposed and retrieved.
- Support image uploads as input.
- Ensure artifact links are directly accessible (sandbox webserver or base64 links).

## Non-goals
- Full object storage integration or multi-region CDN.
- Inline binary streaming in the SSE stream.

## Functional requirements
- Competitors can return an `artifacts` array with metadata + retrieval URL.
- **Artifacts are stored inside the sandbox** and served via a lightweight HTTP server,
  or returned as base64 `data:` URLs for small files (<= 1 MB).
- The sandbox file server MUST expose `/artifacts/*` and serve from a dedicated artifacts
  directory inside the sandbox (e.g. `/workspace/artifacts`).
- Gateway must proxy or serve artifacts locally when needed.
- UI must render artifact links and download buttons.
- Input supports `image_url` or base64 data URLs in message content parts.

## Non-functional requirements
- Artifacts must be size-limited and time-limited (TTL).
- Retrieval must be authenticated or single-use tokenized.
- Artifact links must resolve deterministically to the sandbox file or base64 payload.

## API/contracts
### Artifact descriptor (JSON)
```
{
  "id": "artf_123",
  "type": "image" | "file" | "dataset" | "binary",
  "mime_type": "image/png",
  "display_name": "plot.png",
  "size_bytes": 23123,
  "sha256": "...",
  "created_at": "2026-01-22T12:00:00Z",
  "ttl_seconds": 3600,
  "url": "https://sandbox-host/artifacts/artf_123"
}
```

### Response embedding
- `choices[0].message.artifacts` contains an array of descriptors.
- If `content` references artifacts, it should do so via markdown links to the URL.
- For small artifacts, `url` MAY be a `data:` URL (base64).
 - Markdown links in `content` must resolve to the same URLs found in `artifacts`.

## Data flow
```mermaid
flowchart LR
  COMP[Competitor] -->|artifact metadata| GW[Gateway]
  COMP -->|sandbox file server| SBOX[Sandbox HTTP]
  GW -->|proxy URL or direct sandbox URL| UI[Chat UI]
  UI -->|GET /v1/artifacts/{id}| GW
  GW -->|stream/serve| UI
```

## Acceptance criteria
- Artifact descriptors include `id`, `type`, `mime_type`, `size_bytes`, and `url`.
- If `url` is HTTP:
  - A smoke test fetches the URL and validates content length and SHA256.
- If `url` is `data:`:
  - A unit test decodes base64 and matches the stored SHA256.
- UI renders artifact links with filenames and can download the file.
- Gateway can proxy a sandbox-hosted artifact by ID.

## Open questions / risks
- How should artifact URLs be signed or scoped to a session?
