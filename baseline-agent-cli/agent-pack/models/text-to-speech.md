# Chutes Text-to-Speech API (Kokoro)

Convert text to natural-sounding speech with 54+ voices across 8 languages.

## Endpoint
POST https://chutes-kokoro.chutes.ai/speak

## Authentication
Header: Authorization: Bearer $CHUTES_API_KEY

## Request Body

```json
{
  "text": "Hello, welcome to Janus!",
  "voice": "af_heart",
  "speed": 1.0
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | string | Yes | - | Text to synthesize (max ~5000 chars) |
| `voice` | string | No | af_heart | Voice ID from available voices |
| `speed` | float | No | 1.0 | Speech speed (0.5 to 2.0) |

## Response

Returns audio data (WAV format) directly in the response body.

## Available Voices

### American English (20 voices)

**Female (11):**
| Voice ID | Quality | Description |
|----------|---------|-------------|
| `af_heart` | A | Warm, expressive (recommended) |
| `af_bella` | A- | Clear, professional |
| `af_sarah` | C+ | Natural conversational |
| `af_aoede` | C+ | Melodic tone |
| `af_kore` | C+ | Youthful |
| `af_nicole` | B- | Friendly |
| `af_sky` | C- | Light, airy |
| `af_alloy` | C | Neutral |
| `af_nova` | C | Modern |
| `af_jessica` | D | Standard |
| `af_river` | D | Calm |

**Male (9):**
| Voice ID | Quality | Description |
|----------|---------|-------------|
| `am_fenrir` | C+ | Deep, authoritative |
| `am_michael` | C+ | Professional |
| `am_puck` | C+ | Energetic |
| `am_adam` | F+ | Basic male |
| `am_echo` | D | Standard |
| `am_eric` | D | Neutral |
| `am_liam` | D | Casual |
| `am_onyx` | D | Deep |
| `am_santa` | D- | Jolly (seasonal) |

### British English (8 voices)

**Female:** `bf_alice`, `bf_emma`, `bf_isabella`, `bf_lily`
**Male:** `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`

### Japanese (5 voices)
`jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`

### Mandarin Chinese (8 voices)
**Female:** `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi`
**Male:** `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang`

### Spanish (3 voices)
`ef_dora`, `em_alex`, `em_santa`

### French (1 voice)
`ff_siwis`

### Hindi (4 voices)
**Female:** `hf_alpha`, `hf_beta`
**Male:** `hm_omega`, `hm_psi`

### Italian (2 voices)
`if_sara`, `im_nicola`

### Brazilian Portuguese (3 voices)
`pf_dora`, `pm_alex`, `pm_santa`

## Voice Recommendations by Use Case

| Use Case | Recommended Voice |
|----------|-------------------|
| General assistant | `af_heart` |
| Professional/business | `af_bella`, `am_michael` |
| Storytelling | `bf_emma`, `bm_fable` |
| Tutorials | `af_sarah`, `am_fenrir` |
| Casual/friendly | `af_nicole`, `am_puck` |
| Children's content | `af_kore`, `bf_lily` |

## Example Code

```python
import requests
import os

def text_to_speech(
    text: str,
    voice: str = "af_heart",
    speed: float = 1.0
) -> bytes:
    """Convert text to speech using Kokoro TTS."""
    response = requests.post(
        "https://chutes-kokoro.chutes.ai/speak",
        headers={
            "Authorization": f"Bearer {os.environ['CHUTES_API_KEY']}",
            "Content-Type": "application/json"
        },
        json={
            "text": text,
            "voice": voice,
            "speed": speed
        }
    )
    response.raise_for_status()
    return response.content  # WAV audio bytes

# Generate speech
audio = text_to_speech(
    "Welcome to Janus, the open intelligence rodeo!",
    voice="af_heart",
    speed=1.0
)

# Save to file
with open("welcome.wav", "wb") as f:
    f.write(audio)
```

## Tips for Best Results

1. **Punctuation matters**: Use periods, commas for natural pauses
2. **Numbers**: Spell out numbers for better pronunciation ("twenty-three" vs "23")
3. **Abbreviations**: Expand abbreviations ("Doctor Smith" vs "Dr. Smith")
4. **Emphasis**: Use ALL CAPS sparingly for emphasis
5. **Long text**: Break into paragraphs for more natural flow
