'use client';

import { useState } from 'react';

interface Shortcut {
  label: string;
  instruction: string;
  icon: string;
}

const CODE_SHORTCUTS: Shortcut[] = [
  { label: 'Fix Bugs', instruction: 'Fix any bugs in this code', icon: 'BUG' },
  { label: 'Add Comments', instruction: 'Add helpful comments explaining the code', icon: 'NOTE' },
  { label: 'Optimize', instruction: 'Optimize this code for better performance', icon: 'FAST' },
  { label: 'Add Types', instruction: 'Add type annotations to this code', icon: 'TYPE' },
  { label: 'Add Tests', instruction: 'Generate unit tests for this code', icon: 'TEST' },
  { label: 'Simplify', instruction: 'Simplify this code while maintaining functionality', icon: 'SIM' },
  { label: 'Make Async', instruction: 'Convert this to async/await pattern', icon: 'ASYNC' },
  { label: 'Add Error Handling', instruction: 'Add proper error handling', icon: 'SAFE' },
];

const TEXT_SHORTCUTS: Shortcut[] = [
  { label: 'Make Shorter', instruction: 'Make this text more concise', icon: 'SHORT' },
  { label: 'Make Longer', instruction: 'Expand and elaborate on this text', icon: 'LONG' },
  { label: 'Simplify', instruction: 'Simplify this text for easier understanding', icon: 'SIM' },
  { label: 'More Formal', instruction: 'Make this text more formal and professional', icon: 'FORM' },
  { label: 'More Casual', instruction: 'Make this text more casual and friendly', icon: 'CAS' },
  { label: 'Fix Grammar', instruction: 'Fix grammar and spelling errors', icon: 'GRAM' },
  { label: 'Add Examples', instruction: 'Add examples to illustrate the points', icon: 'EX' },
  { label: 'Summarize', instruction: 'Create a summary of this text', icon: 'SUM' },
];

interface CanvasShortcutsProps {
  language: string;
  onSelect: (instruction: string) => void;
  onClose: () => void;
}

export function CanvasShortcuts({ language, onSelect, onClose }: CanvasShortcutsProps) {
  const shortcuts = language === 'text' ? TEXT_SHORTCUTS : CODE_SHORTCUTS;
  const [customInstruction, setCustomInstruction] = useState('');

  return (
    <div className="canvas-shortcuts" role="dialog" aria-label="AI shortcuts">
      <div className="canvas-shortcuts-header">
        <span>AI Shortcuts</span>
        <button onClick={onClose} className="canvas-shortcuts-close" aria-label="Close shortcuts">
          X
        </button>
      </div>
      <div className="canvas-shortcuts-grid">
        {shortcuts.map((shortcut) => (
          <button
            key={shortcut.label}
            onClick={() => onSelect(shortcut.instruction)}
            className="canvas-shortcut-btn"
          >
            <span className="canvas-shortcut-icon" aria-hidden="true">
              {shortcut.icon}
            </span>
            <span>{shortcut.label}</span>
          </button>
        ))}
      </div>
      <div className="canvas-shortcuts-custom">
        <input
          type="text"
          placeholder="Or type custom instruction..."
          value={customInstruction}
          onChange={(event) => setCustomInstruction(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && customInstruction.trim()) {
              onSelect(customInstruction.trim());
              setCustomInstruction('');
            }
          }}
        />
      </div>
    </div>
  );
}
