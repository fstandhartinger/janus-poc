'use client';

import { useEffect, useRef, useState } from 'react';

export type AgentOption = {
  id: string;
  label: string;
  badges: string[];
};

interface AgentSelectorProps {
  agents: AgentOption[];
  selectedAgent: string;
  onSelect: (agentId: string) => void;
}

export function AgentSelector({ agents, selectedAgent, onSelect }: AgentSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const selectedAgentObj = agents.find((agent) => agent.id === selectedAgent);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  return (
    <div ref={dropdownRef} className="agent-selector">
      <span className="agent-selector-label">Agent</span>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="agent-selector-trigger"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        data-testid="agent-select"
      >
        <span className="agent-selector-value">
          {selectedAgentObj?.label || selectedAgent}
        </span>
        <svg
          className={`agent-selector-chevron ${isOpen ? 'rotate-180' : ''}`}
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
        <div className="agent-selector-dropdown" role="listbox">
          {agents.map((agent) => {
            const isSelected = agent.id === selectedAgent;
            return (
              <button
                key={agent.id}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={`agent-selector-option ${
                  isSelected ? 'agent-selector-option-selected' : ''
                }`}
                onClick={() => {
                  onSelect(agent.id);
                  setIsOpen(false);
                }}
              >
                <div className="agent-selector-option-header">
                  <span className="agent-selector-option-name">{agent.label}</span>
                  {isSelected && (
                    <svg className="agent-selector-check" viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </div>
                <div className="agent-selector-option-badges">
                  {agent.badges.map((badge) => (
                    <span
                      key={`${agent.id}-${badge}`}
                      className={`agent-selector-option-badge ${
                        badge.toLowerCase() === 'tbd' ? 'is-muted' : ''
                      }`}
                    >
                      {badge}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
