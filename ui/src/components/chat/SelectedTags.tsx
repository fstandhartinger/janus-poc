'use client';

import type { GenerationTag } from '@/types/generation';
import { GENERATION_TAG_LABELS } from '@/types/generation';

interface SelectedTagsProps {
  tags: GenerationTag[];
  onRemove: (tag: GenerationTag) => void;
  disabled?: boolean;
}

export function SelectedTags({ tags, onRemove, disabled }: SelectedTagsProps) {
  if (tags.length === 0) return null;

  return (
    <div className="chat-tag-row">
      {tags.map((tag) => (
        <span key={tag} className="chat-tag-chip">
          <span>{GENERATION_TAG_LABELS[tag]}</span>
          <button
            type="button"
            onClick={() => onRemove(tag)}
            className="chat-tag-remove"
            aria-label={`Remove ${GENERATION_TAG_LABELS[tag]} tag`}
            disabled={disabled}
          >
            <XIcon className="w-3 h-3" />
          </button>
        </span>
      ))}
    </div>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6l-12 12" />
    </svg>
  );
}
