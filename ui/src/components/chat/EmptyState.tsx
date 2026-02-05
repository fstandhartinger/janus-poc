'use client';

import { useState } from 'react';
import { DEMO_PROMPTS_BY_CATEGORY } from '@/data/demoPrompts';
import { AllPromptsModal } from './AllPromptsModal';
import { DemoPromptCard } from './DemoPromptCard';

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  const [allPromptsOpen, setAllPromptsOpen] = useState(false);

  const handleSelect = (prompt: string) => {
    onSelectPrompt(prompt);
    setAllPromptsOpen(false);
  };

  const simplePrompts = DEMO_PROMPTS_BY_CATEGORY.simple;
  const researchPrompt = DEMO_PROMPTS_BY_CATEGORY.research[0];
  const agenticPrompt = DEMO_PROMPTS_BY_CATEGORY.agentic[0];
  const multimodalPrompt = DEMO_PROMPTS_BY_CATEGORY.multimodal[0];

  return (
    <div className="chat-empty flex-1">
      <div className="chat-empty-container w-full max-w-4xl px-4 py-6">
        <div className="mb-8 text-center">
          <p className="chat-empty-title">Janus</p>
          <p className="chat-empty-subtitle">The Open Intelligence Rodeo</p>
        </div>

        <div>
          <p className="mb-4 text-center text-sm text-ink-400">Try one of these examples:</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {simplePrompts[0] && (
              <DemoPromptCard prompt={simplePrompts[0]} onSelect={handleSelect} />
            )}
            {researchPrompt && (
              <DemoPromptCard prompt={researchPrompt} onSelect={handleSelect} />
            )}
            {agenticPrompt && (
              <DemoPromptCard
                prompt={agenticPrompt}
                onSelect={handleSelect}
                variant="featured"
                className="sm:col-span-2"
              />
            )}
            {multimodalPrompt && (
              <DemoPromptCard prompt={multimodalPrompt} onSelect={handleSelect} />
            )}
            {simplePrompts[1] && (
              <DemoPromptCard prompt={simplePrompts[1]} onSelect={handleSelect} />
            )}
          </div>

          <button
            type="button"
            className="mx-auto mt-4 block text-sm text-moss/70 transition hover:text-moss"
            onClick={() => setAllPromptsOpen(true)}
            data-testid="see-more-prompts"
          >
            See more examples →
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
