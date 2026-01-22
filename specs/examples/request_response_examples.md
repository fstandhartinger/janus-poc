# Request/Response Examples

## Example 1: Text + Image request
```json
{
  "model": "janus-baseline",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "Describe the chart and summarize trends." },
        { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
      ]
    }
  ],
  "stream": false
}
```

## Example 1 Response
```json
{
  "id": "chatcmpl_01",
  "object": "chat.completion",
  "created": 1769088000,
  "model": "janus-baseline",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The chart shows steady growth in Q2 followed by a plateau in Q3...",
        "artifacts": []
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 542,
    "completion_tokens": 93,
    "total_tokens": 635
  }
}
```

## Example 2: Artifact-producing response
```json
{
  "id": "chatcmpl_02",
  "object": "chat.completion",
  "created": 1769088000,
  "model": "janus-baseline",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I generated a CSV file with the cleaned data: [download](https://gateway.local/v1/artifacts/artf_456)",
        "artifacts": [
          {
            "id": "artf_456",
            "type": "file",
            "mime_type": "text/csv",
            "display_name": "cleaned-data.csv",
            "size_bytes": 4212,
            "sha256": "abc123...",
            "created_at": "2026-01-22T12:00:00Z",
            "ttl_seconds": 3600,
            "url": "https://gateway.local/v1/artifacts/artf_456"
          }
        ]
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 210,
    "completion_tokens": 120,
    "total_tokens": 330,
    "sandbox_seconds": 14.2
  }
}
```
