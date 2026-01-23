# Chutes Text-to-Speech API (Kokoro)

## Endpoint
POST https://chutes-kokoro.chutes.ai/speak

## Request
{
  "text": "Text to synthesize",
  "voice": "af_sky",  // or af_bella, af_sarah, am_adam, am_michael, bf_emma, etc.
  "speed": 1.0       // 0.5 to 2.0
}

## Response
Audio buffer (WAV format) returned directly

## Available Voices
- af_sky, af_bella, af_sarah, af_nicole (American Female)
- am_adam, am_michael (American Male)
- bf_emma, bf_isabella (British Female)
- bm_george, bm_lewis (British Male)
