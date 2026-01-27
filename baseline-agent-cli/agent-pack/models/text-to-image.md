# Chutes Image Generation APIs

## Primary: Qwen Image (router)
POST https://image.chutes.ai/generate
Header: Authorization: Bearer $CHUTES_API_KEY
{
  "model": "qwen-image",
  "prompt": "description of image",
  "width": 1024,
  "height": 1024,
  "num_inference_steps": 30
}
Response: raw image bytes (Content-Type: image/jpeg). Use response.content and base64-encode.

## Alternative: HunYuan (direct)
POST https://chutes-hunyuan-image-3.chutes.ai/generate
Header: Authorization: Bearer $CHUTES_API_KEY
{
  "prompt": "description",
  "size": "auto",
  "steps": 50
}
Response: raw image bytes (Content-Type: image/webp).
