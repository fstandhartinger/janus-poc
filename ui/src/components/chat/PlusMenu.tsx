'use client';

import type { ReactElement } from 'react';
import { useEffect, useRef, useState } from 'react';
import type { GenerationTag } from '@/types/generation';

interface PlusMenuProps {
  onFileSelect: (files: FileList) => void;
  selectedTags: GenerationTag[];
  onTagToggle: (tag: GenerationTag) => void;
  disabled?: boolean;
  accept?: string;
}

type ToggleItem = {
  id: GenerationTag;
  label: string;
  description: string;
  icon: (props: { className?: string }) => ReactElement;
};

const TOGGLE_ITEMS: ToggleItem[] = [
  {
    id: 'generate_image',
    label: 'Generate Image',
    description: 'Create images with AI',
    icon: ImageIcon,
  },
  {
    id: 'generate_video',
    label: 'Generate Video',
    description: 'Create videos with AI',
    icon: VideoIcon,
  },
  {
    id: 'generate_audio',
    label: 'Generate Audio',
    description: 'Create audio or music with AI',
    icon: AudioIcon,
  },
  {
    id: 'deep_research',
    label: 'Deep Research',
    description: 'Comprehensive research with citations',
    icon: SearchIcon,
  },
  {
    id: 'web_search',
    label: 'Web Search',
    description: 'Search the internet for current info',
    icon: GlobeIcon,
  },
];

export function PlusMenu({
  onFileSelect,
  selectedTags,
  onTagToggle,
  disabled,
  accept,
}: PlusMenuProps) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const selectedCount = selectedTags.length;

  useEffect(() => {
    if (!open) return;
    const handleClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (panelRef.current?.contains(target) || buttonRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const handleFileClick = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      onFileSelect(files);
    }
    event.target.value = '';
    setOpen(false);
  };

  return (
    <div className="chat-plus-menu">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        disabled={disabled}
        className="chat-plus-button"
        aria-label="Open plus menu"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <PlusIcon className="w-4 h-4" />
        {selectedCount > 0 && (
          <span className="chat-plus-badge" aria-hidden="true">
            {selectedCount}
          </span>
        )}
      </button>

      {open && (
        <div ref={panelRef} className="chat-plus-panel" role="menu">
          <button
            type="button"
            onClick={handleFileClick}
            className="chat-plus-item"
            role="menuitem"
            disabled={disabled}
          >
            <PaperclipIcon className="w-4 h-4" />
            <span>Attach Files</span>
          </button>

          <div className="chat-plus-divider" role="separator" />

          {TOGGLE_ITEMS.slice(0, 3).map((item) => {
            const isSelected = selectedTags.includes(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onTagToggle(item.id)}
                className={mergeClasses('chat-plus-item chat-plus-toggle', isSelected && 'is-selected')}
                role="menuitemcheckbox"
                aria-checked={isSelected}
                disabled={disabled}
              >
                <item.icon className={mergeClasses('w-4 h-4', isSelected && 'is-selected-icon')} />
                <span className="chat-plus-item-body">
                  <span className="chat-plus-item-label">{item.label}</span>
                  <span className="chat-plus-item-desc">{item.description}</span>
                </span>
                {isSelected && <CheckIcon className="chat-plus-check" />}
              </button>
            );
          })}

          <div className="chat-plus-divider" role="separator" />

          {TOGGLE_ITEMS.slice(3).map((item) => {
            const isSelected = selectedTags.includes(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onTagToggle(item.id)}
                className={mergeClasses('chat-plus-item chat-plus-toggle', isSelected && 'is-selected')}
                role="menuitemcheckbox"
                aria-checked={isSelected}
                disabled={disabled}
              >
                <item.icon className={mergeClasses('w-4 h-4', isSelected && 'is-selected-icon')} />
                <span className="chat-plus-item-body">
                  <span className="chat-plus-item-label">{item.label}</span>
                  <span className="chat-plus-item-desc">{item.description}</span>
                </span>
                {isSelected && <CheckIcon className="chat-plus-check" />}
              </button>
            );
          })}
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={accept}
        className="hidden"
        onChange={handleFileChange}
        disabled={disabled}
        data-testid="file-input"
      />
    </div>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14m7-7H5" />
    </svg>
  );
}

function PaperclipIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8 12.5l6.4-6.4a3 3 0 0 1 4.2 4.2l-7.8 7.8a5 5 0 0 1-7.1-7.1l7.5-7.5"
      />
    </svg>
  );
}

function ImageIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 14l3-3 4 4 3-3 3 3" />
      <circle cx="9" cy="9" r="1.4" />
    </svg>
  );
}

function VideoIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="6" width="14" height="12" rx="2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 10l4-2v8l-4-2" />
    </svg>
  );
}

function AudioIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 8v8" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M16 8v8" />
    </svg>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="11" cy="11" r="6.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 16.5L21 21" />
    </svg>
  );
}

function GlobeIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="12" cy="12" r="9" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h18" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3a14 14 0 0 0 0 18" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3a14 14 0 0 1 0 18" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function mergeClasses(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}
