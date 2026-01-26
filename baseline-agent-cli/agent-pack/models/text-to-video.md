# Chutes Video Generation APIs

## WAN-2.1 Image-to-Video
POST https://chutes-wan2-1-14b.chutes.ai/image2video
Header: Authorization: Bearer $CHUTES_API_KEY
{
  "image": "base64_or_url",
  "prompt": "motion description",
  "negative_prompt": "blur, distortion",
  "num_frames": 81,
  "fps": 16,
  "guidance_scale": 5.0
}
Response: { "video": "base64_video_data", "mime_type": "video/mp4" }

## WAN-2.2 Fast Generation
POST https://chutes-wan-2-2-i2v-14b-fast.chutes.ai/generate
Header: Authorization: Bearer $CHUTES_API_KEY
(similar parameters, optimized for speed)

## LTX-2 Video
POST https://chutes-ltx-video-2.chutes.ai/generate
Header: Authorization: Bearer $CHUTES_API_KEY
{
  "prompt": "video description",
  "negative_prompt": "blur, low quality",
  "width": 768,
  "height": 512,
  "num_frames": 121,
  "seed": -1
}
Response: { "video": "base64_data" }
