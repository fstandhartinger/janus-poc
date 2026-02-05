'use client';

import type { DemoPrompt } from '@/data/demoPrompts';

interface DemoPromptCardProps {
  prompt: DemoPrompt;
  onSelect: (prompt: string) => void;
  variant?: 'compact' | 'featured';
  className?: string;
}

const cx = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(' ');

export function DemoPromptCard({
  prompt,
  onSelect,
  variant = 'compact',
  className,
}: DemoPromptCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(prompt.prompt)}
      className={cx(
        'glass-card group flex h-full flex-col gap-3 p-4 text-left transition',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-moss/50',
        variant === 'featured' && 'border-moss/40 ring-1 ring-moss/25',
        className
      )}
      data-testid={`demo-prompt-${prompt.id}`}
    >
      <div className="flex items-start gap-3">
        {prompt.icon && (
          <span className="text-xl" aria-hidden="true">
            {prompt.icon}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-ink-100 transition-colors group-hover:text-moss">
            {prompt.label}
          </p>
          {prompt.estimatedTime && (
            <p className="mt-1 text-xs text-ink-500">~{prompt.estimatedTime}</p>
          )}
        </div>
      </div>
      {variant === 'featured' && prompt.description && (
        <p className="text-xs leading-relaxed text-ink-400">{prompt.description}</p>
      )}
    </button>
  );
}
