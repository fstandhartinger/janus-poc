# Chutes Lip-Sync API (MuseTalk)

## Endpoint
POST https://chutes-musetalk.chutes.ai/generate
Header: Authorization: Bearer $CHUTES_API_KEY

## Request
{
  "source_image": "base64_portrait_image",
  "audio": "base64_audio_wav",
  "fps": 25
}

## Response
{
  "video": "base64_video_data",
  "mime_type": "video/mp4"
}

## Notes
- Source image should be a clear portrait with visible face
- Audio should be WAV format
- Generates video with lip movements matching audio
