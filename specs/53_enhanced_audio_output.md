# Spec 53: Enhanced Audio Output Support

## Status: DRAFT

## Context / Why

Janus should be a comprehensive multimodal platform supporting various audio outputs:

1. **Text-to-Speech (Kokoro)** - Convert text responses to natural speech
2. **Music Generation (DiffRhythm)** - Generate songs and instrumentals
3. **Sound Effects** - Generate ambient sounds and effects (future)

This spec consolidates audio output capabilities and ensures consistent UI/UX across audio modalities.

## Goals

- Unified audio player component for all audio types
- Enhanced Kokoro TTS documentation with all voices
- Consistent audio handling in chat responses
- Audio download and sharing capabilities

## Non-Goals

- Audio editing/mixing
- Real-time audio streaming during generation
- Audio transcription (covered in speech-to-text spec)

## Functional Requirements

### FR-1: Enhanced TTS Documentation

```markdown
# baseline-agent-cli/agent-pack/models/text-to-speech.md

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
```

### FR-2: Unified Audio Response Component

```tsx
// ui/src/components/audio/AudioResponse.tsx

'use client';

import { useState } from 'react';
import { AudioPlayer } from './AudioPlayer';

interface AudioResponseProps {
  audioUrl: string;  // data:audio/wav;base64,... or URL
  type: 'speech' | 'music' | 'sound';
  title?: string;
  metadata?: {
    voice?: string;
    style?: string;
    duration?: number;
    hasVocals?: boolean;
  };
}

export function AudioResponse({
  audioUrl,
  type,
  title,
  metadata
}: AudioResponseProps) {
  const [expanded, setExpanded] = useState(false);

  const getIcon = () => {
    switch (type) {
      case 'speech': return '🎤';
      case 'music': return '🎵';
      case 'sound': return '🔊';
    }
  };

  const getTypeLabel = () => {
    switch (type) {
      case 'speech': return 'Speech';
      case 'music': return metadata?.hasVocals ? 'Song' : 'Music';
      case 'sound': return 'Sound';
    }
  };

  const getDownloadName = () => {
    const ext = 'wav';
    switch (type) {
      case 'speech': return `speech-${Date.now()}.${ext}`;
      case 'music': return `music-${Date.now()}.${ext}`;
      case 'sound': return `sound-${Date.now()}.${ext}`;
    }
  };

  return (
    <div className={`audio-response audio-response-${type}`}>
      <div className="audio-response-header">
        <span className="audio-response-icon">{getIcon()}</span>
        <span className="audio-response-type">{getTypeLabel()}</span>
        {title && <span className="audio-response-title">{title}</span>}
        {metadata && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="audio-response-details-btn"
          >
            {expanded ? 'Hide details' : 'Details'}
          </button>
        )}
      </div>

      <AudioPlayer
        src={audioUrl}
        downloadName={getDownloadName()}
      />

      {expanded && metadata && (
        <div className="audio-response-metadata">
          {metadata.voice && (
            <div className="metadata-item">
              <span className="metadata-label">Voice:</span>
              <span className="metadata-value">{metadata.voice}</span>
            </div>
          )}
          {metadata.style && (
            <div className="metadata-item">
              <span className="metadata-label">Style:</span>
              <span className="metadata-value">{metadata.style}</span>
            </div>
          )}
          {metadata.duration && (
            <div className="metadata-item">
              <span className="metadata-label">Duration:</span>
              <span className="metadata-value">{formatDuration(metadata.duration)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
```

### FR-3: Audio Detection in Messages

```typescript
// ui/src/lib/audio-parser.ts

export interface ParsedAudio {
  url: string;
  type: 'speech' | 'music' | 'sound';
  title?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Parse audio content from message text.
 *
 * Supports formats:
 * - data:audio/wav;base64,...
 * - :::audio[type=music,title=My Song]
 *   data:audio/wav;base64,...
 *   :::
 */
export function parseAudioContent(content: string): ParsedAudio[] {
  const results: ParsedAudio[] = [];

  // Pattern 1: Custom audio blocks
  const blockRegex = /:::audio\[([^\]]*)\]\n(data:audio\/[^;]+;base64,[A-Za-z0-9+/=]+)\n:::/g;
  let match;

  while ((match = blockRegex.exec(content)) !== null) {
    const attrs = parseAttributes(match[1]);
    results.push({
      url: match[2],
      type: (attrs.type as 'speech' | 'music' | 'sound') || 'sound',
      title: attrs.title,
      metadata: attrs
    });
  }

  // Pattern 2: Inline data URLs (without block)
  const inlineRegex = /(?<!:::audio\[[^\]]*\]\n)(data:audio\/(wav|mp3|ogg);base64,[A-Za-z0-9+/=]+)/g;
  while ((match = inlineRegex.exec(content)) !== null) {
    // Detect type from context
    const contextBefore = content.slice(Math.max(0, match.index - 100), match.index).toLowerCase();
    let type: 'speech' | 'music' | 'sound' = 'sound';

    if (contextBefore.includes('speech') || contextBefore.includes('tts') || contextBefore.includes('spoken')) {
      type = 'speech';
    } else if (contextBefore.includes('music') || contextBefore.includes('song') || contextBefore.includes('melody')) {
      type = 'music';
    }

    results.push({
      url: match[1],
      type
    });
  }

  return results;
}

function parseAttributes(attrString: string): Record<string, string> {
  const attrs: Record<string, string> = {};
  const regex = /(\w+)=([^,\]]+)/g;
  let match;

  while ((match = regex.exec(attrString)) !== null) {
    attrs[match[1]] = match[2];
  }

  return attrs;
}
```

### FR-4: Audio Response Styles

```css
/* ui/src/app/globals.css */

/* Audio Response Container */
.audio-response {
  border-radius: 0.75rem;
  overflow: hidden;
  margin: 0.5rem 0;
}

.audio-response-speech {
  background: linear-gradient(135deg, var(--card-bg) 0%, rgba(99, 210, 151, 0.08) 100%);
  border: 1px solid rgba(99, 210, 151, 0.2);
}

.audio-response-music {
  background: linear-gradient(135deg, var(--card-bg) 0%, rgba(139, 92, 246, 0.08) 100%);
  border: 1px solid rgba(139, 92, 246, 0.2);
}

.audio-response-sound {
  background: linear-gradient(135deg, var(--card-bg) 0%, rgba(59, 130, 246, 0.08) 100%);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.audio-response-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem 0;
}

.audio-response-icon {
  font-size: 1.25rem;
}

.audio-response-type {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}

.audio-response-title {
  font-size: 0.875rem;
  color: var(--text-primary);
  font-weight: 500;
  margin-left: auto;
}

.audio-response-details-btn {
  font-size: 0.75rem;
  color: var(--accent-green);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

.audio-response-details-btn:hover {
  text-decoration: underline;
}

.audio-response .audio-player {
  background: transparent;
  border: none;
  border-radius: 0;
}

.audio-response-metadata {
  padding: 0.5rem 1rem 0.75rem;
  border-top: 1px solid var(--border-color);
  margin-top: 0.5rem;
}

.metadata-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.75rem;
  margin-bottom: 0.25rem;
}

.metadata-label {
  color: var(--text-muted);
}

.metadata-value {
  color: var(--text-secondary);
}
```

### FR-5: LangChain TTS Tool Update

```python
# baseline-langchain/janus_baseline_langchain/tools/tts.py

import os
import base64
import httpx
from langchain.tools import tool

KOKORO_URL = "https://chutes-kokoro.chutes.ai/speak"

# Voice recommendations
VOICES = {
    # American Female
    "af_heart": "Warm, expressive (recommended)",
    "af_bella": "Clear, professional",
    "af_sarah": "Natural conversational",
    "af_nicole": "Friendly",
    "af_sky": "Light, airy",
    # American Male
    "am_fenrir": "Deep, authoritative",
    "am_michael": "Professional",
    "am_puck": "Energetic",
    # British
    "bf_emma": "British female",
    "bm_george": "British male",
    # Other languages
    "jf_alpha": "Japanese female",
    "zf_xiaoxiao": "Chinese female",
    "ef_dora": "Spanish female",
    "ff_siwis": "French female",
}

@tool
def text_to_speech(
    text: str,
    voice: str = "af_heart",
    speed: float = 1.0
) -> str:
    """Convert text to natural speech using Kokoro TTS.

    Args:
        text: Text to convert to speech (max ~5000 chars)
        voice: Voice ID. Options include:
            - af_heart (warm, expressive - default)
            - af_bella (professional)
            - am_michael (male professional)
            - bf_emma (British female)
            - See docs for full list of 54+ voices
        speed: Speech speed from 0.5 (slow) to 2.0 (fast). Default 1.0

    Returns:
        Base64-encoded WAV audio or error message
    """
    api_key = os.environ.get("CHUTES_API_KEY")
    if not api_key:
        return "Error: CHUTES_API_KEY not configured"

    # Validate speed
    speed = max(0.5, min(2.0, speed))

    try:
        response = httpx.post(
            KOKORO_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "voice": voice,
                "speed": speed
            },
            timeout=60.0
        )
        response.raise_for_status()

        audio_b64 = base64.b64encode(response.content).decode()
        return f":::audio[type=speech,voice={voice}]\ndata:audio/wav;base64,{audio_b64}\n:::"

    except httpx.HTTPStatusError as e:
        return f"Error: TTS failed - {e.response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

# Alias for backward compatibility
tts_tool = text_to_speech
```

### FR-6: Agent-CLI TTS Tool Update

```python
# baseline-agent-cli/janus_baseline_agent_cli/tools/tts.py

import os
import base64
import httpx
from typing import Optional

KOKORO_URL = "https://chutes-kokoro.chutes.ai/speak"

async def generate_speech(
    text: str,
    voice: str = "af_heart",
    speed: float = 1.0
) -> dict:
    """Generate speech using Kokoro TTS API.

    Args:
        text: Text to synthesize
        voice: Voice ID (default: af_heart)
        speed: Speech speed 0.5-2.0 (default: 1.0)

    Returns:
        Dict with audio_url (data URI) or error
    """
    api_key = os.environ.get("CHUTES_API_KEY")
    speed = max(0.5, min(2.0, speed))

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            KOKORO_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "voice": voice,
                "speed": speed
            }
        )
        response.raise_for_status()

        audio_b64 = base64.b64encode(response.content).decode()
        return {
            "success": True,
            "audio_url": f"data:audio/wav;base64,{audio_b64}",
            "format": "wav",
            "voice": voice,
            "text_length": len(text)
        }

# Tool definition for agent
TTS_TOOL = {
    "type": "function",
    "function": {
        "name": "text_to_speech",
        "description": "Convert text to natural speech. Supports 54+ voices in 8 languages.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to convert to speech"
                },
                "voice": {
                    "type": "string",
                    "default": "af_heart",
                    "description": "Voice ID (e.g., af_heart, am_michael, bf_emma)"
                },
                "speed": {
                    "type": "number",
                    "default": 1.0,
                    "description": "Speech speed (0.5 to 2.0)"
                }
            },
            "required": ["text"]
        }
    }
}
```

## Non-Functional Requirements

### NFR-1: Performance

- TTS generation < 10 seconds for typical text
- Audio playback starts immediately
- Caching for repeated playback

### NFR-2: File Handling

- Support WAV, MP3, OGG formats
- Base64 for inline embedding
- Download option for all audio

### NFR-3: Accessibility

- Keyboard-accessible audio controls
- ARIA labels on all buttons
- Visual feedback for audio state

## Acceptance Criteria

- [ ] Enhanced TTS documentation with all 54+ voices
- [ ] Unified AudioPlayer component
- [ ] AudioResponse component with type styling
- [ ] Audio detection in message content
- [ ] TTS tools updated in both baselines
- [ ] Download functionality working
- [ ] Mobile-responsive audio players

## Files to Modify/Create

```
baseline-agent-cli/
├── agent-pack/
│   └── models/
│       └── text-to-speech.md           # MODIFY - Enhanced docs
└── janus_baseline_agent_cli/
    └── tools/
        └── tts.py                       # NEW - TTS tool

baseline-langchain/
└── janus_baseline_langchain/
    └── tools/
        └── tts.py                       # MODIFY - Enhanced tool

ui/
└── src/
    ├── components/
    │   └── audio/
    │       ├── AudioPlayer.tsx          # NEW - Base player
    │       └── AudioResponse.tsx        # NEW - Response wrapper
    ├── lib/
    │   └── audio-parser.ts              # NEW - Audio detection
    └── app/
        └── globals.css                  # MODIFY - Audio styles
```

## Related Specs

- `specs/47_text_to_speech_response_playback.md` - TTS playback in UI
- `specs/52_music_generation_diffrhythm.md` - Music generation

## Sources

- [Kokoro-82M Voices](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)
- [Kokoro HuggingFace Space](https://huggingface.co/spaces/hexgrad/Kokoro-TTS)
