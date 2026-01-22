# Artifacts and File Handling

## Context / Why
Janus supports "anything out" outputs, but the MVP will surface non-text outputs as
artifact descriptors and retrieval URLs. This document defines the artifact schema and
how uploads/downloads work.

## Goals
- Define an artifact descriptor schema.
- Specify how artifact URLs are exposed and retrieved.
- Support image uploads as input.

## Non-goals
- Full object storage integration or multi-region CDN.
- Inline binary streaming in the SSE stream.

## Functional requirements
- Competitors can return an `artifacts` array with metadata + retrieval URL.
- Gateway must proxy or serve artifacts locally.
- UI must render artifact links and download buttons.
- Input supports `image_url` or base64 data URLs in message content parts.

## Non-functional requirements
- Artifacts must be size-limited and time-limited (TTL).
- Retrieval must be authenticated or single-use tokenized.

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
  "url": "https://gateway.local/v1/artifacts/artf_123"
}
```

### Response embedding
- `choices[0].message.artifacts` contains an array of descriptors.
- If `content` references artifacts, it should do so via markdown links to the URL.

## Data flow
```mermaid
flowchart LR
  COMP[Competitor] -->|artifact metadata| GW[Gateway]
  GW -->|proxy URL| UI[Chat UI]
  UI -->|GET /v1/artifacts/{id}| GW
  GW -->|stream/serve| UI
```

## Acceptance criteria
- Artifact descriptors include `id`, `type`, `mime_type`, `size_bytes`, and `url`.
- UI renders artifact links with filenames.
- Gateway can serve a locally stored artifact by ID.

## Open questions / risks
- Where should artifacts be stored in PoC (disk vs object storage)?
- How should artifact URLs be signed or scoped to a session?
