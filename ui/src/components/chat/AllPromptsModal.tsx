'use client';

import { useEffect } from 'react';
import { DEMO_PROMPTS_BY_CATEGORY, type DemoPrompt } from '@/data/demoPrompts';

interface AllPromptsModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (prompt: string) => void;
}

interface PromptButtonProps {
  prompt: DemoPrompt;
  onSelect: (prompt: string) => void;
  showTime?: boolean;
}

function PromptButton({ prompt, onSelect, showTime }: PromptButtonProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(prompt.prompt)}
      className="flex w-full items-start gap-3 rounded-xl border border-ink-800/70 bg-ink-900/40 p-3 text-left transition hover:border-moss/40"
      data-testid={`all-prompts-${prompt.id}`}
    >
      {prompt.icon && (
        <span className="text-lg" aria-hidden="true">
          {prompt.icon}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-ink-100">{prompt.label}</p>
        <p className="mt-1 text-xs text-ink-400">{prompt.prompt}</p>
        {showTime && prompt.estimatedTime && (
          <p className="mt-1 text-xs text-moss">~{prompt.estimatedTime}</p>
        )}
      </div>
    </button>
  );
}

export function AllPromptsModal({ open, onClose, onSelect }: AllPromptsModalProps) {
  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  const handleSelect = (prompt: string) => {
    onSelect(prompt);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 dialog-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-prompts-title"
      onClick={onClose}
      data-testid="all-prompts-modal"
    >
      <div
        className="glass-card w-full max-w-3xl max-h-[85vh] overflow-y-auto p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <h2 id="demo-prompts-title" className="text-lg font-semibold text-ink-100">
            Example Prompts
          </h2>
          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-ink-800/70 text-ink-400 transition hover:text-ink-100"
            onClick={onClose}
            aria-label="Close example prompts"
          >
            ✕
          </button>
        </div>

        <div className="space-y-6">
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
              Quick Questions
            </h3>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {DEMO_PROMPTS_BY_CATEGORY.simple.map((prompt) => (
                <PromptButton key={prompt.id} prompt={prompt} onSelect={handleSelect} />
              ))}
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
              Agentic Tasks
            </h3>
            <div className="space-y-2">
              {DEMO_PROMPTS_BY_CATEGORY.agentic.map((prompt) => (
                <PromptButton
                  key={prompt.id}
                  prompt={prompt}
                  onSelect={handleSelect}
                  showTime
                />
              ))}
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
              Research
            </h3>
            <div className="space-y-2">
              {DEMO_PROMPTS_BY_CATEGORY.research.map((prompt) => (
                <PromptButton
                  key={prompt.id}
                  prompt={prompt}
                  onSelect={handleSelect}
                  showTime
                />
              ))}
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
              Multimodal
            </h3>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {DEMO_PROMPTS_BY_CATEGORY.multimodal.map((prompt) => (
                <PromptButton
                  key={prompt.id}
                  prompt={prompt}
                  onSelect={handleSelect}
                  showTime
                />
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
