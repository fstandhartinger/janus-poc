'use client';

import { useMemo } from 'react';
import { DEMO_PROMPTS, type DemoPrompt } from '@/data/demoPrompts';

interface QuickSuggestionsProps {
  onSelect: (prompt: string) => void;
  visible: boolean;
}

const shufflePrompts = (items: DemoPrompt[]) => {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
};

export function QuickSuggestions({ onSelect, visible }: QuickSuggestionsProps) {
  const suggestions = useMemo(() => shufflePrompts(DEMO_PROMPTS).slice(0, 4), []);

  if (!visible) return null;

  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {suggestions.map((prompt) => (
        <button
          key={prompt.id}
          type="button"
          onClick={() => onSelect(prompt.prompt)}
          className="flex items-center gap-2 rounded-full border border-ink-800/70 bg-ink-900/40 px-3 py-1.5 text-xs text-ink-300 transition hover:border-moss/40 hover:text-ink-100"
          data-testid={`quick-suggestion-${prompt.id}`}
        >
          <span aria-hidden="true">{prompt.icon}</span>
          <span className="truncate">{prompt.label}</span>
        </button>
      ))}
    </div>
  );
}
