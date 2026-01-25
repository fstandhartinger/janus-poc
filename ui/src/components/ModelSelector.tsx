'use client';

import { useState, useRef, useEffect } from 'react';
import type { Model } from '@/types/chat';

interface ModelSelectorProps {
  models: Model[];
  selectedModel: string;
  onSelect: (modelId: string) => void;
}

export function ModelSelector({ models, selectedModel, onSelect }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const selectedModelObj = models.find((m) => m.id === selectedModel);

  return (
    <div ref={dropdownRef} className="model-selector">
      <span className="model-selector-label">Model</span>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="model-selector-trigger"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        data-testid="model-select"
      >
        <span className="model-selector-value">
          {selectedModelObj?.id || selectedModel}
        </span>
        <svg
          className={`model-selector-chevron ${isOpen ? 'rotate-180' : ''}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="model-selector-dropdown" role="listbox">
          {models.map((model) => (
            <button
              key={model.id}
              type="button"
              role="option"
              aria-selected={model.id === selectedModel}
              className={`model-selector-option ${
                model.id === selectedModel ? 'model-selector-option-selected' : ''
              }`}
              onClick={() => {
                onSelect(model.id);
                setIsOpen(false);
              }}
            >
              <span className="model-selector-option-name">{model.id}</span>
              {model.id.includes('langchain') && (
                <span className="model-selector-option-badge">LangChain</span>
              )}
              {model.id.includes('cli-agent') && (
                <span className="model-selector-option-badge">CLI</span>
              )}
              {model.id === selectedModel && (
                <svg className="model-selector-check" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
