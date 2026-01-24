# Spec 78: Plus Menu with Generation Tags

**Status:** NOT STARTED
**Priority:** High
**Complexity:** High
**Prerequisites:** None

---

## Overview

Extend the "+" button in the chat textarea to show a menu similar to ChatGPT's, allowing users to:
1. Attach files (existing functionality)
2. Select generation tags/flags: "Generate Image", "Generate Video", "Generate Audio"
3. Additional features like "Deep Research", "Web Search"

These tags are sent as flags in the HTTP request body to the baseline Janus model. The complexity detector recognizes these flags and ensures the agent path is used, with the agent informed of the user's intent via prompt modification.

---

## Functional Requirements

### FR-1: Plus Menu Component

Replace simple file input with expandable menu.

**Menu Structure (inspired by ChatGPT):**
```
┌─────────────────────────────┐
│ 📎 Attach Files             │
│ 📷 Take Screenshot          │  (future)
├─────────────────────────────┤
│ 🎨 Generate Image           │
│ 🎬 Generate Video           │
│ 🔊 Generate Audio           │
├─────────────────────────────┤
│ 🔍 Deep Research            │
│ 🌐 Web Search               │
├─────────────────────────────┤
│ ⚙️ More...                  │ → submenu
└─────────────────────────────┘
```

**Component:**
```tsx
// components/chat/PlusMenu.tsx
interface PlusMenuProps {
  onFileSelect: (files: FileList) => void;
  selectedTags: GenerationTag[];
  onTagToggle: (tag: GenerationTag) => void;
}

type GenerationTag =
  | 'generate_image'
  | 'generate_video'
  | 'generate_audio'
  | 'deep_research'
  | 'web_search';

const MENU_ITEMS: MenuItem[] = [
  {
    type: 'action',
    id: 'attach_files',
    icon: Paperclip,
    label: 'Attach Files',
    action: 'file_select',
  },
  { type: 'separator' },
  {
    type: 'toggle',
    id: 'generate_image',
    icon: ImageIcon,
    label: 'Generate Image',
    description: 'Create images with AI',
  },
  {
    type: 'toggle',
    id: 'generate_video',
    icon: Video,
    label: 'Generate Video',
    description: 'Create videos with AI',
  },
  {
    type: 'toggle',
    id: 'generate_audio',
    icon: Volume2,
    label: 'Generate Audio',
    description: 'Create audio/music with AI',
  },
  { type: 'separator' },
  {
    type: 'toggle',
    id: 'deep_research',
    icon: Search,
    label: 'Deep Research',
    description: 'Comprehensive research with citations',
  },
  {
    type: 'toggle',
    id: 'web_search',
    icon: Globe,
    label: 'Web Search',
    description: 'Search the internet for current info',
  },
];

export function PlusMenu({ onFileSelect, selectedTags, onTagToggle }: PlusMenuProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Plus className="w-5 h-5" />
          {selectedTags.length > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-moss-500 rounded-full text-[10px] flex items-center justify-center">
              {selectedTags.length}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64 glass-card">
        {MENU_ITEMS.map((item, index) => {
          if (item.type === 'separator') {
            return <DropdownMenuSeparator key={index} />;
          }

          if (item.type === 'action' && item.action === 'file_select') {
            return (
              <DropdownMenuItem
                key={item.id}
                onClick={() => fileInputRef.current?.click()}
              >
                <item.icon className="w-4 h-4 mr-2" />
                {item.label}
              </DropdownMenuItem>
            );
          }

          if (item.type === 'toggle') {
            const isSelected = selectedTags.includes(item.id as GenerationTag);
            return (
              <DropdownMenuItem
                key={item.id}
                onClick={() => onTagToggle(item.id as GenerationTag)}
                className={cn(isSelected && 'bg-moss-500/20')}
              >
                <item.icon className={cn(
                  "w-4 h-4 mr-2",
                  isSelected && "text-moss-500"
                )} />
                <div className="flex-1">
                  <p className="text-sm">{item.label}</p>
                  <p className="text-xs text-gray-400">{item.description}</p>
                </div>
                {isSelected && <Check className="w-4 h-4 text-moss-500" />}
              </DropdownMenuItem>
            );
          }
          return null;
        })}
      </DropdownMenuContent>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => e.target.files && onFileSelect(e.target.files)}
      />
    </DropdownMenu>
  );
}
```

### FR-2: Selected Tags Display

Show selected tags as chips/badges below the textarea.

```tsx
// components/chat/SelectedTags.tsx
export function SelectedTags({ tags, onRemove }: SelectedTagsProps) {
  if (tags.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1 px-3 pb-2">
      {tags.map((tag) => (
        <Badge
          key={tag}
          variant="secondary"
          className="bg-moss-500/20 text-moss-400 gap-1"
        >
          {TAG_LABELS[tag]}
          <button onClick={() => onRemove(tag)} className="hover:text-white">
            <X className="w-3 h-3" />
          </button>
        </Badge>
      ))}
    </div>
  );
}

const TAG_LABELS: Record<GenerationTag, string> = {
  generate_image: '🎨 Image',
  generate_video: '🎬 Video',
  generate_audio: '🔊 Audio',
  deep_research: '🔍 Research',
  web_search: '🌐 Search',
};
```

### FR-3: Extended Chat Request Model

Add generation flags to the request body.

**TypeScript (UI):**
```typescript
interface ChatRequest {
  model: string;
  messages: Message[];
  stream: boolean;
  user_id?: string;
  enable_memory?: boolean;
  // NEW: Generation flags
  generation_flags?: {
    generate_image?: boolean;
    generate_video?: boolean;
    generate_audio?: boolean;
    deep_research?: boolean;
    web_search?: boolean;
  };
}
```

**Python (Baseline):**
```python
class GenerationFlags(BaseModel):
    generate_image: bool = False
    generate_video: bool = False
    generate_audio: bool = False
    deep_research: bool = False
    web_search: bool = False

class ChatCompletionRequest(BaseModel):
    # ... existing fields ...
    generation_flags: GenerationFlags | None = None
```

### FR-4: Complexity Detector Integration

Update complexity detector to recognize generation flags.

```python
# services/complexity.py

def analyze(self, messages: list[Message], flags: GenerationFlags | None = None) -> ComplexityAnalysis:
    """Analyze message complexity including generation flags."""

    # Check generation flags FIRST - these always require agent
    if flags:
        flag_reasons = []
        if flags.generate_image:
            flag_reasons.append("image generation requested")
        if flags.generate_video:
            flag_reasons.append("video generation requested")
        if flags.generate_audio:
            flag_reasons.append("audio generation requested")
        if flags.deep_research:
            flag_reasons.append("deep research requested")
        if flags.web_search:
            flag_reasons.append("web search requested")

        if flag_reasons:
            return ComplexityAnalysis(
                is_complex=True,
                reason=f"generation_flags: {', '.join(flag_reasons)}",
                keywords_matched=flag_reasons,
                multimodal_detected=False,
            )

    # Continue with normal keyword/LLM analysis...
```

### FR-5: Agent Prompt Modification

When generation flags are set, prepend instructions to the user's message.

```python
def _build_agent_prompt(
    user_message: str,
    flags: GenerationFlags | None,
) -> str:
    """Build agent prompt with generation flag instructions."""

    instructions = []

    if flags:
        if flags.generate_image:
            instructions.append(
                "The user has explicitly requested IMAGE GENERATION. "
                "You MUST generate one or more images as part of your response using the Chutes image API."
            )
        if flags.generate_video:
            instructions.append(
                "The user has explicitly requested VIDEO GENERATION. "
                "You MUST generate a video as part of your response using the Chutes video API."
            )
        if flags.generate_audio:
            instructions.append(
                "The user has explicitly requested AUDIO GENERATION. "
                "You MUST generate audio (speech/music) as part of your response using the Chutes TTS/audio API."
            )
        if flags.deep_research:
            instructions.append(
                "The user has explicitly requested DEEP RESEARCH. "
                "You MUST perform comprehensive research with citations using chutes-search max mode."
            )
        if flags.web_search:
            instructions.append(
                "The user has explicitly requested WEB SEARCH. "
                "You MUST search the internet for current information to answer this query."
            )

    if not instructions:
        return user_message

    instruction_block = "\n".join(f"- {i}" for i in instructions)

    return f"""______ Generation Instructions ______
The user has enabled the following generation modes:
{instruction_block}

Please ensure your response includes the requested generated content.
_____________________________________

{user_message}"""
```

### FR-6: Stream Response with Tag Indicators

Include information about which generation modes are active in SSE stream.

```python
# Initial SSE chunk includes metadata
{
  "id": "chatcmpl-xxx",
  "model": "baseline",
  "metadata": {
    "generation_flags": {
      "generate_image": true,
      "generate_video": false,
      "generate_audio": false,
      "deep_research": false,
      "web_search": true
    },
    "using_agent": true,
    "complexity_reason": "generation_flags: image generation requested, web search requested"
  },
  "choices": [...]
}
```

---

## Technical Requirements

### TR-1: UI Components

| File | Purpose |
|------|---------|
| `ui/src/components/chat/PlusMenu.tsx` | Expandable plus menu |
| `ui/src/components/chat/SelectedTags.tsx` | Tag badges display |
| `ui/src/types/chat.ts` | GenerationTag type definitions |

### TR-2: State Management

```tsx
// In chat page or useChat hook
const [selectedTags, setSelectedTags] = useState<GenerationTag[]>([]);

const toggleTag = (tag: GenerationTag) => {
  setSelectedTags((prev) =>
    prev.includes(tag)
      ? prev.filter((t) => t !== tag)
      : [...prev, tag]
  );
};

// Clear tags after sending message
const sendMessage = async () => {
  await submitChat({
    messages: [...],
    generation_flags: {
      generate_image: selectedTags.includes('generate_image'),
      generate_video: selectedTags.includes('generate_video'),
      generate_audio: selectedTags.includes('generate_audio'),
      deep_research: selectedTags.includes('deep_research'),
      web_search: selectedTags.includes('web_search'),
    },
  });
  setSelectedTags([]); // Clear after send
};
```

### TR-3: Baseline Implementation Changes

**baseline-agent-cli:**
- `models.py` - Add `GenerationFlags` model
- `main.py` - Pass flags to complexity detector
- `services/complexity.py` - Check flags first
- `services/sandy.py` - Prepend instructions to prompt

**baseline-langchain:**
- Same changes mirrored

---

## Files to Create

| File | Purpose |
|------|---------|
| `ui/src/components/chat/PlusMenu.tsx` | Plus menu component |
| `ui/src/components/chat/SelectedTags.tsx` | Tag display component |
| `ui/src/types/generation.ts` | Type definitions |

## Files to Modify

| File | Changes |
|------|---------|
| `ui/src/components/ChatInput.tsx` | Replace + button with PlusMenu |
| `ui/src/hooks/useChat.ts` | Add tag state and pass to request |
| `ui/src/app/api/chat/route.ts` | Forward generation_flags |
| `baseline-agent-cli/janus_baseline_agent_cli/models.py` | Add GenerationFlags |
| `baseline-agent-cli/janus_baseline_agent_cli/main.py` | Handle flags |
| `baseline-agent-cli/janus_baseline_agent_cli/services/complexity.py` | Check flags |
| `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py` | Prepend instructions |
| `baseline-langchain/...` | Mirror all changes |

---

## UI/UX Design

### Plus Menu (Closed)

```
[+] Write a message...                    [🎤] [📤]
```

### Plus Menu (Open)

```
┌─────────────────────────────┐
│ 📎 Attach Files             │
├─────────────────────────────┤
│ 🎨 Generate Image           │
│ 🎬 Generate Video           │
│ 🔊 Generate Audio           │
├─────────────────────────────┤
│ 🔍 Deep Research            │
│ 🌐 Web Search               │
└─────────────────────────────┘
[+] Write a message...                    [🎤] [📤]
```

### With Selected Tags

```
[🎨 Image ×] [🔍 Research ×]
[+] Write a message...                    [🎤] [📤]
```

### Menu Item States

**Normal:** Gray icon, white text
**Hovered:** Slight background highlight
**Selected:** Moss green icon, green background tint, checkmark

---

## Acceptance Criteria

- [ ] Plus button shows expandable menu
- [ ] File attachment still works
- [ ] Generation tags can be toggled on/off
- [ ] Selected tags show as badges
- [ ] Tags clear after message sent
- [ ] `generation_flags` included in request body
- [ ] Complexity detector recognizes flags
- [ ] Agent receives generation instructions in prompt
- [ ] Works in both baseline implementations

---

## Testing Checklist

- [ ] Menu opens on click
- [ ] File attachment triggers file picker
- [ ] Each tag toggles correctly
- [ ] Multiple tags can be selected
- [ ] Tags display as badges
- [ ] Tags can be removed from badges
- [ ] Network request includes `generation_flags`
- [ ] Agent path is used when flags set
- [ ] Agent response includes generated content
- [ ] Tags reset after send

---

## Notes

- Generation tags are "hints" to the agent, not strict requirements
- The agent may generate content even without explicit flags
- Flags ensure the agent path is used (never fast path)
- Consider adding visual feedback when generation is in progress
- Future: Add tag presets (e.g., "Creative Mode" = image + audio)
