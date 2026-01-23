# Spec 21: Enhanced Baseline Implementation

## Status: COMPLETE

## Context

The reference implementation (baseline competitor) currently uses a minimal system prompt that doesn't fully leverage CLI agent capabilities. Inspired by the `chutes-knowledge-agent` project, we should enhance the baseline to:

1. Encourage the CLI agent to use its full potential (filesystem, web search, code execution)
2. Provide MD reference files documenting Chutes model APIs for agent discovery
3. Create a system prompt that links to these resources and encourages tool usage

## Requirements

### 21.1 Agent Pack Reference Files

Create a `baseline/agent-pack/` directory with comprehensive MD reference files:

#### 21.1.1 `models/text-to-speech.md`
Document the Kokoro TTS API:
```markdown
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
```

#### 21.1.2 `models/text-to-image.md`
Document image generation APIs:
```markdown
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
```

#### 21.1.3 `models/text-to-video.md`
Document video generation APIs:
```markdown
# Chutes Video Generation APIs

## WAN-2.1 Image-to-Video
POST https://chutes-wan2-1-14b.chutes.ai/image2video
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
(similar parameters, optimized for speed)

## LTX-2 Video
POST https://chutes-ltx-video-2.chutes.ai/generate
{
  "prompt": "video description",
  "negative_prompt": "blur, low quality",
  "width": 768,
  "height": 512,
  "num_frames": 121,
  "seed": -1
}
Response: { "video": "base64_data" }
```

#### 21.1.4 `models/lip-sync.md`
Document the MuseTalk API:
```markdown
# Chutes Lip-Sync API (MuseTalk)

## Endpoint
POST https://chutes-musetalk.chutes.ai/generate

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
```

#### 21.1.5 `models/llm.md`
Document available LLM models:
```markdown
# Chutes LLM Endpoint

## Endpoint
POST https://llm.chutes.ai/v1/chat/completions

## OpenAI-Compatible Request
{
  "model": "deepseek-ai/DeepSeek-V3-0324",
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": true
}

## Available Models
- deepseek-ai/DeepSeek-V3-0324 (latest)
- deepseek-ai/DeepSeek-V3.2-TEE (secure enclave)
- Various open models via Chutes marketplace
```

### 21.2 Enhanced System Prompt

Update `baseline/janus_baseline/prompts/system.md`:

```markdown
You are a Janus baseline agent with full access to coding tools and research capabilities.

## Your Capabilities
You are ENCOURAGED to use all available tools to provide the best assistance:
- **File tools**: Read, write, search, and explore files in your workspace
- **Web search**: Search the web for documentation, examples, or solutions
- **Code execution**: Write and run code to test solutions or demonstrate concepts
- **Shell commands**: Run bash commands for git, npm, pip, curl, etc.

## Reference Documentation
Your workspace contains comprehensive API documentation for Chutes services:

- `docs/models/text-to-speech.md` - Kokoro TTS API
- `docs/models/text-to-image.md` - Qwen/HunYuan image generation
- `docs/models/text-to-video.md` - WAN-2/LTX video generation
- `docs/models/lip-sync.md` - MuseTalk lip-sync API
- `docs/models/llm.md` - Chutes LLM endpoint

When users ask about generating media (images, audio, video), ALWAYS check these docs first!

## How to Work
1. **Research first**: Explore available documentation and examples
2. **Use tools actively**: Don't just describe - actually do it when possible
3. **Test your work**: Run code to verify solutions before presenting them
4. **Be thorough**: Use web search if local docs are insufficient
5. **Cite sources**: Reference documentation files and URLs

## Guidelines
- Think step-by-step for complex problems
- Write clean, working code
- Handle errors gracefully
- Don't expose secrets or API keys
- Ask for clarification only when genuinely stuck
```

### 21.3 Agent Pack Bootstrap

Create `baseline/agent-pack/bootstrap.sh`:

```bash
#!/bin/bash
# Bootstrap script run when agent starts in sandbox

# Create docs directory structure
mkdir -p /workspace/docs/models

# Copy reference documentation
cp /agent-pack/models/*.md /workspace/docs/models/

# Set up environment
export PYTHONDONTWRITEBYTECODE=1
export NODE_NO_WARNINGS=1

echo "Agent pack initialized. Reference docs available at /workspace/docs/"
```

### 21.4 Configuration Updates

Update `baseline/janus_baseline/config.py`:
```python
class Settings(BaseSettings):
    # Existing settings...

    # Agent pack configuration
    agent_pack_path: str = "./agent-pack"
    system_prompt_path: str = "./agent-pack/prompts/system.md"
    enable_web_search: bool = True
    enable_code_execution: bool = True
    enable_file_tools: bool = True
```

### 21.5 Sandy Integration Updates

Update `baseline/janus_baseline/services/sandy.py` to:
1. Mount the agent-pack directory into the sandbox
2. Run bootstrap.sh before starting the agent
3. Pass enhanced configuration to the CLI agent

## Acceptance Criteria

- [ ] Agent pack directory exists with all model reference MD files
- [ ] System prompt encourages tool usage (file, web, code, shell)
- [ ] System prompt references the model documentation files
- [ ] Bootstrap script copies docs to workspace on sandbox creation
- [ ] Agent can read and use model documentation to answer media generation questions
- [ ] Configuration supports toggling capabilities
- [ ] Integration test: Agent answers "How do I generate an image with Chutes?" using local docs
- [ ] Integration test: Agent writes working code that calls a Chutes API

## Test Plan

### Unit Tests
- Test agent pack file structure exists
- Test system prompt loading
- Test configuration validation

### Integration Tests
- Create sandbox, verify bootstrap ran
- Ask agent about image generation, verify it reads docs/models/text-to-image.md
- Ask agent to write code for TTS, verify it produces correct API call

### Smoke Tests
- Full request through gateway → baseline with media generation question
- Verify reasoning_content shows agent reading documentation files
- Verify final response includes accurate API information

## Dependencies

- Spec 09 (reference implementation) - must be complete
- Sandy sandbox service - must support file mounting

## Notes

This enhancement transforms the baseline from a simple LLM wrapper into a capable research assistant that can:
1. Discover and use Chutes APIs via documentation
2. Write and test code
3. Search the web for additional context
4. Provide comprehensive, accurate answers about media generation

The pattern follows the successful `chutes-knowledge-agent` approach of giving agents explicit permission and resources to use their full capabilities.
