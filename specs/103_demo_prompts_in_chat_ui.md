# Spec 103: Pre-Built Demo Prompts in Chat UI

## Status: COMPLETE

## Context / Why

First-time visitors to https://janus.rodeo don't know what to ask. They need inspiration and quick ways to see Janus's capabilities. Pre-built demo prompts solve this by:
1. Showcasing capabilities immediately
2. Reducing friction to first interaction
3. Demonstrating both fast path and agentic capabilities

## Goals

- Add clickable demo prompts to the chat UI
- Cover all key capabilities (simple, agentic, research, multimodal)
- Make it easy for users to try Janus without thinking of prompts
- Show prompts in empty chat state and optionally as suggestions

## Demo Prompts

### Category 1: Simple Questions (Fast Path)
```typescript
const SIMPLE_PROMPTS = [
  {
    label: "Explain",
    prompt: "Explain why the sky is blue",
    icon: "💡",
    category: "simple",
  },
  {
    label: "Compare",
    prompt: "Compare Python and JavaScript for web development",
    icon: "⚖️",
    category: "simple",
  },
  {
    label: "Translate",
    prompt: "Translate 'Hello, how are you?' to German, French, and Japanese",
    icon: "🌍",
    category: "simple",
  },
];
```

### Category 2: Agentic Tasks
```typescript
const AGENTIC_PROMPTS = [
  {
    label: "Clone & Summarize",
    prompt: "Clone the https://github.com/anthropics/anthropic-cookbook repository and summarize what it contains",
    icon: "📦",
    category: "agentic",
    estimatedTime: "1-2 min",
  },
  {
    label: "Analyze Code",
    prompt: "Clone https://github.com/fastapi/fastapi and explain the project structure",
    icon: "🔍",
    category: "agentic",
    estimatedTime: "1-2 min",
  },
  {
    label: "Download & Process",
    prompt: "Download the README from https://github.com/langchain-ai/langchain and create a summary document",
    icon: "📄",
    category: "agentic",
    estimatedTime: "30-60s",
  },
];
```

### Category 3: Research
```typescript
const RESEARCH_PROMPTS = [
  {
    label: "Web Research",
    prompt: "Search the web for the latest AI developments in 2026 and write a brief report with sources",
    icon: "🔎",
    category: "research",
    estimatedTime: "30-60s",
  },
  {
    label: "Deep Dive",
    prompt: "Research the pros and cons of Rust vs Go for backend development and give me a detailed comparison",
    icon: "📊",
    category: "research",
    estimatedTime: "1-2 min",
  },
  {
    label: "News Summary",
    prompt: "Find the top tech news from this week and summarize the key stories",
    icon: "📰",
    category: "research",
    estimatedTime: "30-60s",
  },
];
```

### Category 4: Multimodal
```typescript
const MULTIMODAL_PROMPTS = [
  {
    label: "Generate Image",
    prompt: "Generate an image of a futuristic city with flying cars at sunset",
    icon: "🎨",
    category: "multimodal",
    estimatedTime: "10-20s",
  },
  {
    label: "Create Art",
    prompt: "Generate an image of a cozy cabin in a snowy forest at night with northern lights",
    icon: "🖼️",
    category: "multimodal",
    estimatedTime: "10-20s",
  },
  {
    label: "Read Aloud",
    prompt: "Write a short poem about the ocean and read it aloud",
    icon: "🔊",
    category: "multimodal",
    estimatedTime: "15-30s",
  },
];
```

## Functional Requirements

### FR-1: Demo Prompt Data Structure

```typescript
// ui/src/data/demoPrompts.ts

export interface DemoPrompt {
  id: string;
  label: string;           // Short button label
  prompt: string;          // Full prompt text
  icon: string;            // Emoji or icon
  category: 'simple' | 'agentic' | 'research' | 'multimodal';
  estimatedTime?: string;  // e.g., "10-20s", "1-2 min"
  description?: string;    // Tooltip description
}

export const DEMO_PROMPTS: DemoPrompt[] = [
  // Simple
  {
    id: 'simple-explain',
    label: 'Explain why it rains',
    prompt: 'Explain why it rains in simple terms',
    icon: '🌧️',
    category: 'simple',
    description: 'Quick explanation - uses fast LLM path',
  },
  {
    id: 'simple-joke',
    label: 'Tell me a joke',
    prompt: 'Tell me a clever programming joke',
    icon: '😄',
    category: 'simple',
  },

  // Agentic
  {
    id: 'agentic-clone',
    label: 'Clone & analyze repo',
    prompt: 'Clone the https://github.com/anthropics/anthropic-cookbook repository and give me a summary of what it contains',
    icon: '📦',
    category: 'agentic',
    estimatedTime: '1-2 min',
    description: 'Spawns agent to clone repo and analyze files',
  },

  // Research
  {
    id: 'research-web',
    label: 'Web research report',
    prompt: 'Search the web for the latest developments in quantum computing and write me a brief report with sources',
    icon: '🔎',
    category: 'research',
    estimatedTime: '30-60s',
    description: 'Searches web and synthesizes findings',
  },

  // Multimodal
  {
    id: 'multimodal-image',
    label: 'Generate an image',
    prompt: 'Generate an image of a futuristic city with flying cars at sunset',
    icon: '🎨',
    category: 'multimodal',
    estimatedTime: '10-20s',
    description: 'Creates image using AI generation',
  },
];

// Grouped for UI display
export const DEMO_PROMPTS_BY_CATEGORY = {
  simple: DEMO_PROMPTS.filter(p => p.category === 'simple'),
  agentic: DEMO_PROMPTS.filter(p => p.category === 'agentic'),
  research: DEMO_PROMPTS.filter(p => p.category === 'research'),
  multimodal: DEMO_PROMPTS.filter(p => p.category === 'multimodal'),
};
```

### FR-2: Empty State with Demo Prompts

```typescript
// ui/src/components/chat/EmptyState.tsx

import { DEMO_PROMPTS_BY_CATEGORY, DemoPrompt } from '@/data/demoPrompts';

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      {/* Logo/Title */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">
          Janus
        </h1>
        <p className="text-white/60">
          The Open Intelligence Rodeo
        </p>
      </div>

      {/* Demo Prompts Grid */}
      <div className="w-full max-w-2xl">
        <p className="text-sm text-white/40 mb-4 text-center">
          Try one of these examples:
        </p>

        <div className="grid grid-cols-2 gap-3">
          {/* Simple - quick demos */}
          <DemoPromptCard
            prompt={DEMO_PROMPTS_BY_CATEGORY.simple[0]}
            onClick={onSelectPrompt}
            variant="compact"
          />

          {/* Research */}
          <DemoPromptCard
            prompt={DEMO_PROMPTS_BY_CATEGORY.research[0]}
            onClick={onSelectPrompt}
            variant="compact"
          />

          {/* Agentic - highlight this one */}
          <DemoPromptCard
            prompt={DEMO_PROMPTS_BY_CATEGORY.agentic[0]}
            onClick={onSelectPrompt}
            variant="featured"
            className="col-span-2"
          />

          {/* Multimodal */}
          <DemoPromptCard
            prompt={DEMO_PROMPTS_BY_CATEGORY.multimodal[0]}
            onClick={onSelectPrompt}
            variant="compact"
          />

          {/* Another simple */}
          <DemoPromptCard
            prompt={DEMO_PROMPTS_BY_CATEGORY.simple[1]}
            onClick={onSelectPrompt}
            variant="compact"
          />
        </div>

        {/* More prompts link */}
        <button
          className="mt-4 text-sm text-moss-green/60 hover:text-moss-green mx-auto block"
          onClick={() => {/* Show all prompts modal */}}
        >
          See more examples →
        </button>
      </div>
    </div>
  );
}

interface DemoPromptCardProps {
  prompt: DemoPrompt;
  onClick: (prompt: string) => void;
  variant?: 'compact' | 'featured';
  className?: string;
}

function DemoPromptCard({ prompt, onClick, variant = 'compact', className }: DemoPromptCardProps) {
  return (
    <button
      onClick={() => onClick(prompt.prompt)}
      className={cn(
        "glass-card p-4 text-left hover:border-moss-green/50 transition-colors group",
        variant === 'featured' && "border-moss-green/30",
        className
      )}
    >
      <div className="flex items-start gap-3">
        <span className="text-xl">{prompt.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate group-hover:text-moss-green transition-colors">
            {prompt.label}
          </p>
          {prompt.estimatedTime && (
            <p className="text-xs text-white/40 mt-1">
              ~{prompt.estimatedTime}
            </p>
          )}
        </div>
      </div>
      {variant === 'featured' && prompt.description && (
        <p className="text-sm text-white/50 mt-2">
          {prompt.description}
        </p>
      )}
    </button>
  );
}
```

### FR-3: Integrate with Chat Area

```typescript
// ui/src/components/ChatArea.tsx

import { EmptyState } from './chat/EmptyState';

export function ChatArea() {
  const { messages, sendMessage } = useChat();

  const handleSelectPrompt = (prompt: string) => {
    sendMessage(prompt);
  };

  return (
    <div className="flex flex-col h-full">
      {messages.length === 0 ? (
        <EmptyState onSelectPrompt={handleSelectPrompt} />
      ) : (
        <MessageList messages={messages} />
      )}

      <ChatInput onSend={sendMessage} />
    </div>
  );
}
```

### FR-4: Quick Suggestions Above Input (Optional)

```typescript
// ui/src/components/chat/QuickSuggestions.tsx

// Show 3-4 quick suggestions above the input when chat is empty or after response

interface QuickSuggestionsProps {
  onSelect: (prompt: string) => void;
  visible: boolean;
}

export function QuickSuggestions({ onSelect, visible }: QuickSuggestionsProps) {
  if (!visible) return null;

  // Show random subset of prompts
  const suggestions = useMemo(() => {
    return shuffle(DEMO_PROMPTS).slice(0, 4);
  }, []);

  return (
    <div className="flex flex-wrap gap-2 px-4 py-2">
      {suggestions.map(prompt => (
        <button
          key={prompt.id}
          onClick={() => onSelect(prompt.prompt)}
          className="px-3 py-1.5 text-sm rounded-full bg-white/5 hover:bg-white/10
                     text-white/70 hover:text-white transition-colors"
        >
          {prompt.icon} {prompt.label}
        </button>
      ))}
    </div>
  );
}
```

### FR-5: All Prompts Modal

```typescript
// ui/src/components/chat/AllPromptsModal.tsx

export function AllPromptsModal({ open, onClose, onSelect }: AllPromptsModalProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="glass-card max-w-2xl">
        <DialogHeader>
          <DialogTitle>Example Prompts</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Simple */}
          <section>
            <h3 className="text-sm font-medium text-white/60 mb-2">
              💡 Quick Questions
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_PROMPTS_BY_CATEGORY.simple.map(p => (
                <PromptButton key={p.id} prompt={p} onSelect={onSelect} />
              ))}
            </div>
          </section>

          {/* Agentic */}
          <section>
            <h3 className="text-sm font-medium text-white/60 mb-2">
              🤖 Agentic Tasks
            </h3>
            <div className="space-y-2">
              {DEMO_PROMPTS_BY_CATEGORY.agentic.map(p => (
                <PromptButton key={p.id} prompt={p} onSelect={onSelect} showTime />
              ))}
            </div>
          </section>

          {/* Research */}
          <section>
            <h3 className="text-sm font-medium text-white/60 mb-2">
              🔎 Research
            </h3>
            <div className="space-y-2">
              {DEMO_PROMPTS_BY_CATEGORY.research.map(p => (
                <PromptButton key={p.id} prompt={p} onSelect={onSelect} showTime />
              ))}
            </div>
          </section>

          {/* Multimodal */}
          <section>
            <h3 className="text-sm font-medium text-white/60 mb-2">
              🎨 Multimodal
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_PROMPTS_BY_CATEGORY.multimodal.map(p => (
                <PromptButton key={p.id} prompt={p} onSelect={onSelect} showTime />
              ))}
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

## Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                         🤠 Janus                            │
│                 The Open Intelligence Rodeo                 │
│                                                             │
│               Try one of these examples:                    │
│                                                             │
│   ┌───────────────────┐  ┌───────────────────┐             │
│   │ 🌧️ Explain why    │  │ 🔎 Web research   │             │
│   │    it rains       │  │    report         │             │
│   │                   │  │    ~30-60s        │             │
│   └───────────────────┘  └───────────────────┘             │
│                                                             │
│   ┌─────────────────────────────────────────────┐          │
│   │ 📦 Clone & analyze repo                      │          │
│   │    Clone a GitHub repository and summarize   │          │
│   │    its contents        ~1-2 min             │          │
│   └─────────────────────────────────────────────┘          │
│                                                             │
│   ┌───────────────────┐  ┌───────────────────┐             │
│   │ 🎨 Generate an    │  │ 😄 Tell me a      │             │
│   │    image          │  │    joke           │             │
│   │    ~10-20s        │  │                   │             │
│   └───────────────────┘  └───────────────────┘             │
│                                                             │
│                   See more examples →                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Message Janus...                              🎤 📎 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Acceptance Criteria

- [ ] Empty state shows demo prompts grid
- [ ] Clicking a demo prompt sends it as a message
- [ ] All 4 categories represented (simple, agentic, research, multimodal)
- [ ] Featured prompt (agentic) is visually highlighted
- [ ] "See more examples" opens modal with all prompts
- [ ] Mobile responsive layout
- [ ] Demo prompts actually work when clicked (tested)

## Files to Create

```
ui/src/
├── data/
│   └── demoPrompts.ts           # NEW: Prompt data
├── components/
│   └── chat/
│       ├── EmptyState.tsx       # NEW: Empty state with prompts
│       ├── DemoPromptCard.tsx   # NEW: Individual prompt card
│       ├── QuickSuggestions.tsx # NEW: Suggestions above input
│       └── AllPromptsModal.tsx  # NEW: All prompts modal
└── components/
    └── ChatArea.tsx             # MODIFY: Integrate EmptyState
```

## Testing

```typescript
// Playwright E2E test
test('demo prompts work', async ({ page }) => {
  await page.goto('/chat');

  // Should see empty state with prompts
  await expect(page.getByText('Explain why it rains')).toBeVisible();

  // Click a simple prompt
  await page.click('text=Explain why it rains');

  // Should start streaming response
  await expect(page.locator('.message-assistant')).toBeVisible({ timeout: 5000 });

  // Response should contain relevant content
  await expect(page.locator('.message-assistant')).toContainText(/water|evapor|cloud/i, { timeout: 30000 });
});
```

## Related Specs

- Spec 102: Core Demo Use Cases
- Spec 11: Chat UI
- Spec 28: Chat UI Improvements

NR_OF_TRIES: 1
