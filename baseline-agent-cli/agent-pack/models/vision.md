# Vision Models on Chutes

## Available Models

### Primary: Qwen3-VL-235B-A22B-Instruct
- Model ID: `Qwen/Qwen3-VL-235B-A22B-Instruct`
- Capabilities: Image understanding, OCR, diagram analysis, visual QA
- Context: 32k tokens
- Best for: Complex visual reasoning, detailed image analysis

### Fallback: Mistral-Small-3.2-24B-Instruct-2506
- Model ID: `chutesai/Mistral-Small-3.2-24B-Instruct-2506`
- Capabilities: Basic image understanding, visual QA
- Context: 128k tokens
- Best for: Simple image questions, faster responses

## Usage

Images are passed as part of the message content array:

```python
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,..."
                }
            }
        ]
    }
]
```

## Image Formats Supported

- JPEG, PNG, GIF, WebP
- Base64 data URLs
- HTTP/HTTPS URLs (external images)

## Detail Levels

The `detail` parameter controls image processing:
- "low": 512x512 max, faster processing
- "high": Native resolution, better for OCR/details
- "auto" (default): Automatic selection based on image

## Best Practices

1. Use "low" detail for simple "what is this?" questions
2. Use "high" detail for OCR, reading text, diagrams
3. Limit image count - most tasks need only 1-2 images
4. Compress large images - base64 adds ~33% overhead
