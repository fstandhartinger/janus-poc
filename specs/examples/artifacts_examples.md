# Artifact Examples

## Image artifact
```json
{
  "id": "artf_img_001",
  "type": "image",
  "mime_type": "image/png",
  "display_name": "chart.png",
  "size_bytes": 128732,
  "sha256": "9d1c...",
  "created_at": "2026-01-22T12:00:00Z",
  "ttl_seconds": 3600,
  "url": "https://sandbox-abc.sandy.local/artifacts/chart.png"
}
```

## File artifact
```json
{
  "id": "artf_file_010",
  "type": "file",
  "mime_type": "application/pdf",
  "display_name": "report.pdf",
  "size_bytes": 98231,
  "sha256": "fa12...",
  "created_at": "2026-01-22T12:00:00Z",
  "ttl_seconds": 3600,
  "url": "data:application/pdf;base64,JVBERi0xLjcKJcfs..."
}
```

## Dataset artifact
```json
{
  "id": "artf_data_007",
  "type": "dataset",
  "mime_type": "application/json",
  "display_name": "results.json",
  "size_bytes": 4201,
  "sha256": "bc33...",
  "created_at": "2026-01-22T12:00:00Z",
  "ttl_seconds": 3600,
  "url": "https://gateway.local/v1/artifacts/artf_data_007"
}
```
