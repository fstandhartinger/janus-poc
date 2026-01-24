# Chutes Music Generation API (DiffRhythm)

Generate full-length songs with vocals and instrumentals, or pure instrumental music.

## Endpoint
POST https://chutes-diffrhythm.chutes.ai/generate

## Authentication
Header: Authorization: Bearer $CHUTES_API_KEY

## Request Body

```json
{
  "steps": 32,
  "lyrics": "[00:00.00] First line of lyrics\n[00:05.00] Second line...",
  "style_prompt": "Pop emotional piano ballad with soft drums"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `steps` | int | No | Diffusion steps (default: 32, higher = better quality but slower) |
| `lyrics` | string | No | LRC format lyrics with timestamps. Null for instrumental. |
| `style_prompt` | string | No | Musical style description |

### Style Prompt Examples

**Genre-based:**
- "Pop emotional piano ballad"
- "Indie folk with acoustic guitar picking and harmonica"
- "Jazz nightclub vibe with smooth saxophone"
- "Electronic dance music with heavy bass drops"
- "Classical orchestral piece with strings and woodwinds"
- "Rock anthem with distorted guitars and powerful drums"
- "Hip-hop beat with trap-style hi-hats"
- "Ambient electronic with ethereal synths"

**Mood-based:**
- "Upbeat and energetic summer vibes"
- "Melancholic and introspective"
- "Epic and cinematic"
- "Calm and peaceful meditation music"
- "Dark and mysterious atmosphere"

**Specific descriptions:**
- "80s synthwave with retro keyboards and gated reverb drums"
- "Acoustic folk ballad, coming-of-age themes, fingerpicking guitar"
- "Lo-fi hip-hop study beats with vinyl crackle"

### Lyrics Format (LRC)

Lyrics use LRC timestamp format:
```
[00:00.00] First verse line one
[00:04.50] First verse line two
[00:09.00] First verse line three
[00:13.50]
[00:14.00] Chorus line one
[00:18.00] Chorus line two
```

**Tips for lyrics:**
- Keep lines rhythmic and natural-sounding
- Match syllable count to intended rhythm
- Leave gaps between sections (verses, chorus)
- Include empty timestamps `[00:13.50]` for pauses

### Instrumental Mode

Set `lyrics: null` for pure instrumental generation:
```json
{
  "steps": 32,
  "lyrics": null,
  "style_prompt": "Jazzy piano lounge music"
}
```

## Response

Returns audio data (WAV format) directly in the response body.

## Example Code

```python
import os
import requests

def generate_music(
    style_prompt: str,
    lyrics: str | None = None,
    steps: int = 32
) -> bytes:
    """Generate music using DiffRhythm."""
    response = requests.post(
        "https://chutes-diffrhythm.chutes.ai/generate",
        headers={
            "Authorization": f"Bearer {os.environ['CHUTES_API_KEY']}",
            "Content-Type": "application/json"
        },
        json={
            "steps": steps,
            "lyrics": lyrics,
            "style_prompt": style_prompt
        }
    )
    response.raise_for_status()
    return response.content  # WAV audio bytes

# Generate instrumental
audio = generate_music(
    style_prompt="Calm lo-fi beats for studying",
    lyrics=None
)

# Save to file
with open("output.wav", "wb") as f:
    f.write(audio)

# Generate song with lyrics
lyrics = """[00:00.00] Walking down the street today
[00:04.00] Thinking about what you said
[00:08.00] Every word still echoes here
[00:12.00] Playing back inside my head"""

audio = generate_music(
    style_prompt="Indie pop with acoustic guitar",
    lyrics=lyrics
)
```

## Quality Tips

1. **Style prompts**: Be specific about instruments, mood, and genre
2. **Steps**: 32 is good balance; 50+ for higher quality
3. **Lyrics**: Match rhythm to intended tempo
4. **Language**: Works best with English; Chinese also supported
