# Chutes Image Generation APIs

## Primary: Qwen QVQ
POST https://image.chutes.ai/generate
{
  "prompt": "description of image",
  "width": 1024,
  "height": 1024,
  "steps": 30
}
Response: { "b64_json": "base64_image_data" }

## Alternative: HunYuan
POST https://chutes-hunyuan-image-3.chutes.ai/generate
{
  "prompt": "description",
  "width": 1024,
  "height": 1024,
  "num_inference_steps": 30
}
Response: { "image": "base64_data" }
