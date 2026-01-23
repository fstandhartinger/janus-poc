# Spec 52: Music Generation with DiffRhythm

## Status: DRAFT

## Context / Why

DiffRhythm is a state-of-the-art open-source music generation model that can create full-length songs (up to 4m45s) with synchronized vocals and instrumentals in seconds. Adding music generation expands Janus's multimodal capabilities significantly.

Use cases:
- Generate background music for videos
- Create jingles and short audio clips
- Produce demo tracks with custom lyrics
- Generate instrumental music for content creators

## Goals

- Integrate DiffRhythm API for music generation
- Support both vocal songs (with lyrics) and instrumentals
- Document model usage for agents
- Display audio player in chat UI
- Enable download of generated music

## Non-Goals

- Real-time music streaming during generation
- Music editing/remixing capabilities
- MIDI output

## Functional Requirements

### FR-1: Model Documentation for Agent

```markdown
# baseline-agent-cli/agent-pack/models/music-generation.md

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
import requests
import os

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
```

### FR-2: LangChain Tool

```python
# baseline-langchain/janus_baseline_langchain/tools/music_gen.py

import os
import base64
import httpx
from langchain.tools import tool

DIFFRHYTHM_URL = "https://chutes-diffrhythm.chutes.ai/generate"

@tool
def music_generation(
    style_prompt: str,
    lyrics: str = None,
    steps: int = 32
) -> str:
    """Generate music using DiffRhythm.

    Args:
        style_prompt: Musical style description (e.g., "Pop ballad with piano")
        lyrics: Optional LRC format lyrics with timestamps. Omit for instrumental.
        steps: Diffusion steps (32 default, higher = better quality)

    Returns:
        Base64-encoded WAV audio or error message
    """
    api_key = os.environ.get("CHUTES_API_KEY")
    if not api_key:
        return "Error: CHUTES_API_KEY not configured"

    try:
        response = httpx.post(
            DIFFRHYTHM_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "steps": steps,
                "lyrics": lyrics,
                "style_prompt": style_prompt
            },
            timeout=120.0  # Music generation can take time
        )
        response.raise_for_status()

        # Return base64-encoded audio for embedding in response
        audio_b64 = base64.b64encode(response.content).decode()
        return f"data:audio/wav;base64,{audio_b64}"

    except httpx.HTTPStatusError as e:
        return f"Error: Music generation failed - {e.response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

# Alias
music_gen_tool = music_generation
```

### FR-3: Agent-CLI Tool

```python
# baseline-agent-cli/janus_baseline_agent_cli/tools/music.py

import os
import base64
import httpx
from typing import Optional

DIFFRHYTHM_URL = "https://chutes-diffrhythm.chutes.ai/generate"

async def generate_music(
    style_prompt: str,
    lyrics: Optional[str] = None,
    steps: int = 32
) -> dict:
    """Generate music using DiffRhythm API.

    Args:
        style_prompt: Musical style description
        lyrics: Optional LRC format lyrics (null for instrumental)
        steps: Diffusion steps

    Returns:
        Dict with audio_url (data URI) or error
    """
    api_key = os.environ.get("CHUTES_API_KEY")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            DIFFRHYTHM_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "steps": steps,
                "lyrics": lyrics,
                "style_prompt": style_prompt
            }
        )
        response.raise_for_status()

        audio_b64 = base64.b64encode(response.content).decode()
        return {
            "success": True,
            "audio_url": f"data:audio/wav;base64,{audio_b64}",
            "format": "wav",
            "style": style_prompt,
            "has_vocals": lyrics is not None
        }

# Tool definition for agent
MUSIC_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_music",
        "description": "Generate music or songs using AI. Can create instrumentals or full songs with vocals.",
        "parameters": {
            "type": "object",
            "properties": {
                "style_prompt": {
                    "type": "string",
                    "description": "Musical style (e.g., 'Pop ballad with piano', 'Lo-fi hip-hop beats')"
                },
                "lyrics": {
                    "type": "string",
                    "description": "LRC format lyrics with timestamps. Omit for instrumental."
                },
                "steps": {
                    "type": "integer",
                    "default": 32,
                    "description": "Quality steps (32 default, 50+ for higher quality)"
                }
            },
            "required": ["style_prompt"]
        }
    }
}
```

### FR-4: Chat UI Audio Player

```tsx
// ui/src/components/AudioPlayer.tsx

'use client';

import { useState, useRef, useEffect } from 'react';

interface AudioPlayerProps {
  src: string;  // data:audio/wav;base64,... or URL
  title?: string;
  downloadName?: string;
}

export function AudioPlayer({ src, title, downloadName = 'audio.wav' }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateProgress = () => {
      setCurrentTime(audio.currentTime);
      setProgress((audio.currentTime / audio.duration) * 100);
    };

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
    };

    audio.addEventListener('timeupdate', updateProgress);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateProgress);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    audio.currentTime = percent * audio.duration;
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = src;
    link.download = downloadName;
    link.click();
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="audio-player">
      <audio ref={audioRef} src={src} preload="metadata" />

      {title && <div className="audio-title">{title}</div>}

      <div className="audio-controls">
        <button onClick={togglePlay} className="audio-play-btn">
          {isPlaying ? <PauseIcon /> : <PlayIcon />}
        </button>

        <div className="audio-progress-container" onClick={handleSeek}>
          <div className="audio-progress-bar">
            <div
              className="audio-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="audio-time">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>

        <button onClick={handleDownload} className="audio-download-btn" title="Download">
          <DownloadIcon />
        </button>
      </div>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  );
}
```

### FR-5: Audio Player Styles

```css
/* ui/src/app/globals.css */

/* Audio Player */
.audio-player {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  padding: 1rem;
  margin: 0.5rem 0;
}

.audio-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}

.audio-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.audio-play-btn {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-green);
  border: none;
  border-radius: 50%;
  color: var(--bg-primary);
  cursor: pointer;
  transition: transform 0.1s ease;
}

.audio-play-btn:hover {
  transform: scale(1.05);
}

.audio-progress-container {
  flex: 1;
  cursor: pointer;
  padding: 0.5rem 0;
}

.audio-progress-bar {
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
}

.audio-progress-fill {
  height: 100%;
  background: var(--accent-green);
  transition: width 0.1s linear;
}

.audio-time {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  min-width: 80px;
  text-align: right;
}

.audio-download-btn {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.audio-download-btn:hover {
  background: var(--card-bg-hover);
  color: var(--text-primary);
}

/* Music player variant with waveform visualization */
.music-player {
  background: linear-gradient(135deg, var(--card-bg) 0%, rgba(99, 210, 151, 0.05) 100%);
}

.music-player .audio-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.music-player .audio-title::before {
  content: '🎵';
}
```

### FR-6: Message Content Parser Update

```tsx
// ui/src/components/MessageBubble.tsx

// Add audio detection in message content
function parseAudioContent(content: string) {
  const audioRegex = /data:audio\/(wav|mp3|ogg);base64,[A-Za-z0-9+/=]+/g;
  const matches = content.match(audioRegex);
  return matches || [];
}

// In render:
{audioUrls.map((url, i) => (
  <AudioPlayer
    key={i}
    src={url}
    title={`Generated Audio ${i + 1}`}
    downloadName={`audio-${i + 1}.wav`}
  />
))}
```

## Non-Functional Requirements

### NFR-1: Performance

- Music generation timeout: 120 seconds max
- Audio files cached for replay
- Progressive loading indicator

### NFR-2: File Size

- Generated audio typically 5-50MB
- Use base64 for inline display
- Offer download for large files

### NFR-3: Quality

- Default 32 steps for fast generation
- Option for 50+ steps for production quality

## Acceptance Criteria

- [ ] Music generation API integrated in both baselines
- [ ] Agent documentation file created
- [ ] Audio player component working in chat UI
- [ ] Supports both instrumental and vocal modes
- [ ] Download functionality working
- [ ] Progress/loading indicator during generation

## Files to Modify/Create

```
baseline-agent-cli/
├── agent-pack/
│   └── models/
│       └── music-generation.md      # NEW - Agent docs
└── janus_baseline_agent_cli/
    └── tools/
        └── music.py                 # NEW - Music tool

baseline-langchain/
└── janus_baseline_langchain/
    └── tools/
        └── music_gen.py             # NEW - LangChain tool

ui/
└── src/
    ├── components/
    │   └── AudioPlayer.tsx          # NEW - Audio player
    └── app/
        └── globals.css              # MODIFY - Audio styles
```

## Related Specs

- `specs/47_text_to_speech_response_playback.md` - TTS playback
- `specs/53_enhanced_audio_output.md` - Complete audio support

## Sources

- [DiffRhythm HuggingFace](https://huggingface.co/blog/Dzkaka/diffrhythm-open-source-ai-music-generator)
- [DiffRhythm GitHub](https://github.com/ASLP-lab/DiffRhythm)
- [DiffRhythm Paper](https://arxiv.org/html/2503.01183v1)
