'use client';

import { useState } from 'react';
import { DEMO_PROMPTS_BY_CATEGORY } from '@/data/demoPrompts';
import { AllPromptsModal } from './AllPromptsModal';

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

// Curated quick-starts — short, text-only pills. Keeps the empty state calm
// and matches the chutes-frontend minimal "Ask anything…" aesthetic.
const QUICK_PROMPTS: Array<{ id: string; label: string; prompt: string }> = [
  {
    id: 'sky',
    label: 'Explain why the sky is blue',
    prompt: DEMO_PROMPTS_BY_CATEGORY.simple[0]?.prompt ?? 'Explain why the sky is blue.',
  },
  {
    id: 'research',
    label: 'Web research report',
    prompt:
      DEMO_PROMPTS_BY_CATEGORY.research[0]?.prompt ??
      'Research the latest advances in AI agents and give me a brief report.',
  },
  {
    id: 'repo',
    label: 'Clone & summarize a repo',
    prompt:
      DEMO_PROMPTS_BY_CATEGORY.agentic[0]?.prompt ??
      'Clone https://github.com/chutesai/chutes and summarize the repository structure.',
  },
  {
    id: 'image',
    label: 'Generate a futuristic city',
    prompt:
      DEMO_PROMPTS_BY_CATEGORY.multimodal[0]?.prompt ??
      'Generate an image of a futuristic city at dusk.',
  },
];

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  const [allPromptsOpen, setAllPromptsOpen] = useState(false);

  const handleSelect = (prompt: string) => {
    onSelectPrompt(prompt);
    setAllPromptsOpen(false);
  };

  return (
    <div className="chat-empty flex-1">
      <div className="chat-empty-container w-full max-w-2xl mx-auto px-4">
        <p className="chat-empty-title">Where should we begin?</p>

        <div className="chat-empty-prompts" role="list">
          {QUICK_PROMPTS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="chat-empty-prompt"
              onClick={() => handleSelect(item.prompt)}
              role="listitem"
            >
              {item.label}
            </button>
          ))}
          <button
            type="button"
            className="chat-empty-prompt chat-empty-prompt-more"
            onClick={() => setAllPromptsOpen(true)}
            data-testid="see-more-prompts"
          >
            More examples →
          </button>
        </div>
      </div>

      <AllPromptsModal
        open={allPromptsOpen}
        onClose={() => setAllPromptsOpen(false)}
        onSelect={handleSelect}
      />
    </div>
  );
}
