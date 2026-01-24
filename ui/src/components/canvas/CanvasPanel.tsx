'use client';

import { useState } from 'react';
import { useCanvasStore } from '@/store/canvas';
import { CanvasEditor } from './CanvasEditor';
import { CanvasHistory } from './CanvasHistory';
import { CanvasShortcuts } from './CanvasShortcuts';

interface CanvasPanelProps {
  onAIEdit: (instruction: string) => void;
  disabled?: boolean;
}

export function CanvasPanel({ onAIEdit, disabled = false }: CanvasPanelProps) {
  const { isOpen, closeCanvas, getActiveDocument, updateContent } = useCanvasStore();
  const [showHistory, setShowHistory] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);

  const doc = getActiveDocument();

  if (!isOpen || !doc) return null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(doc.content);
  };

  const handleDownload = () => {
    const ext = getExtension(doc.language);
    const filename = doc.title.includes('.') ? doc.title : `${doc.title}${ext}`;
    const blob = new Blob([doc.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleShortcut = (instruction: string) => {
    onAIEdit(instruction);
    setShowShortcuts(false);
  };

  return (
    <div className="canvas-panel" aria-label="Canvas editor">
      <div className="canvas-header">
        <div className="canvas-title">
          <span className="canvas-icon" aria-hidden="true">
            {doc.language === 'text' ? <DocIcon /> : <CodeIcon />}
          </span>
          <span>{doc.title}</span>
          {doc.readonly && <span className="canvas-readonly">Read only</span>}
        </div>

        <div className="canvas-actions">
          <button
            onClick={() => setShowShortcuts((current) => !current)}
            title="AI Shortcuts"
            aria-label="AI shortcuts"
            disabled={disabled || doc.readonly}
          >
            <MagicIcon />
          </button>
          <button
            onClick={() => setShowHistory((current) => !current)}
            title="Version History"
            aria-label="Version history"
          >
            <HistoryIcon />
          </button>
          <button onClick={handleCopy} title="Copy to Clipboard" aria-label="Copy to clipboard">
            <CopyIcon />
          </button>
          <button onClick={handleDownload} title="Download" aria-label="Download">
            <DownloadIcon />
          </button>
          <button onClick={closeCanvas} title="Close Canvas" aria-label="Close canvas">
            <CloseIcon />
          </button>
        </div>
      </div>

      {showShortcuts && (
        <CanvasShortcuts
          language={doc.language}
          onSelect={handleShortcut}
          onClose={() => setShowShortcuts(false)}
        />
      )}

      <CanvasEditor
        content={doc.content}
        language={doc.language}
        readonly={doc.readonly}
        onChange={(nextContent) => updateContent(nextContent, 'User edit')}
      />

      {showHistory && (
        <CanvasHistory
          versions={doc.versions}
          currentVersionId={doc.currentVersionId}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  );
}

function getExtension(language: string): string {
  const extensions: Record<string, string> = {
    python: '.py',
    javascript: '.js',
    typescript: '.ts',
    html: '.html',
    css: '.css',
    json: '.json',
    markdown: '.md',
    text: '.txt',
  };
  return extensions[language] || '.txt';
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />
    </svg>
  );
}

function MagicIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8L19 13M17.8 6.2L19 5M3 21l9-9" />
    </svg>
  );
}

function HistoryIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}
