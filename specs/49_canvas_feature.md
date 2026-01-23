# Spec 49: Canvas Feature

## Status: DRAFT

## Context / Why

ChatGPT Canvas popularized a side-panel editing interface where users can:
- See generated content (documents, code) in an editable panel
- Make direct edits while collaborating with AI
- Track version history
- Use shortcuts for common adjustments (simplify, expand, fix bugs, etc.)

This spec implements a similar Canvas feature for Janus, enabling collaborative document/code editing.

## Goals

- Side-panel editor that opens alongside chat
- Support for text documents and code files
- Direct editing by user
- AI-assisted editing via shortcuts
- Version history with restore capability
- Copy/download functionality

## Non-Goals

- Real-time collaborative editing (multi-user)
- Full IDE features (debugging, git integration)
- Complex document formats (DOCX, PDF editing)

## Functional Requirements

### FR-1: Canvas Protocol

Define how the agent signals canvas content:

```markdown
<!-- In assistant message, agent wraps canvas content -->

I've created a Python script for you:

:::canvas[language=python,title=data_processor.py]
import pandas as pd

def process_data(filepath: str) -> pd.DataFrame:
    """Load and clean data from CSV file."""
    df = pd.read_csv(filepath)

    # Remove duplicates
    df = df.drop_duplicates()

    # Handle missing values
    df = df.fillna(0)

    return df

if __name__ == "__main__":
    result = process_data("input.csv")
    print(f"Processed {len(result)} rows")
:::

You can edit this directly in the canvas panel, or ask me to make changes!
```

Canvas metadata attributes:
- `language` - Code language (python, javascript, etc.) or `text` for documents
- `title` - File name or document title
- `readonly` - If true, canvas is view-only

### FR-2: Canvas State Store

```typescript
// ui/src/store/canvas.ts

import { create } from 'zustand';

export interface CanvasVersion {
  id: string;
  content: string;
  timestamp: number;
  description: string;
}

export interface CanvasDocument {
  id: string;
  title: string;
  language: string;
  content: string;
  versions: CanvasVersion[];
  currentVersionId: string;
  createdAt: number;
  updatedAt: number;
}

interface CanvasState {
  documents: Map<string, CanvasDocument>;
  activeDocumentId: string | null;
  isOpen: boolean;

  // Actions
  openCanvas: (doc: CanvasDocument) => void;
  closeCanvas: () => void;
  updateContent: (content: string, description?: string) => void;
  restoreVersion: (versionId: string) => void;
  createDocument: (title: string, language: string, content: string) => string;
  getActiveDocument: () => CanvasDocument | null;
}

export const useCanvasStore = create<CanvasState>((set, get) => ({
  documents: new Map(),
  activeDocumentId: null,
  isOpen: false,

  openCanvas: (doc) => {
    const documents = new Map(get().documents);
    documents.set(doc.id, doc);
    set({ documents, activeDocumentId: doc.id, isOpen: true });
  },

  closeCanvas: () => {
    set({ isOpen: false });
  },

  updateContent: (content, description = 'Edit') => {
    const { activeDocumentId, documents } = get();
    if (!activeDocumentId) return;

    const doc = documents.get(activeDocumentId);
    if (!doc) return;

    const newVersion: CanvasVersion = {
      id: crypto.randomUUID(),
      content,
      timestamp: Date.now(),
      description,
    };

    const updatedDoc: CanvasDocument = {
      ...doc,
      content,
      versions: [...doc.versions, newVersion],
      currentVersionId: newVersion.id,
      updatedAt: Date.now(),
    };

    const newDocuments = new Map(documents);
    newDocuments.set(activeDocumentId, updatedDoc);
    set({ documents: newDocuments });
  },

  restoreVersion: (versionId) => {
    const { activeDocumentId, documents } = get();
    if (!activeDocumentId) return;

    const doc = documents.get(activeDocumentId);
    if (!doc) return;

    const version = doc.versions.find((v) => v.id === versionId);
    if (!version) return;

    const newVersion: CanvasVersion = {
      id: crypto.randomUUID(),
      content: version.content,
      timestamp: Date.now(),
      description: `Restored from ${new Date(version.timestamp).toLocaleString()}`,
    };

    const updatedDoc: CanvasDocument = {
      ...doc,
      content: version.content,
      versions: [...doc.versions, newVersion],
      currentVersionId: newVersion.id,
      updatedAt: Date.now(),
    };

    const newDocuments = new Map(documents);
    newDocuments.set(activeDocumentId, updatedDoc);
    set({ documents: newDocuments });
  },

  createDocument: (title, language, content) => {
    const id = crypto.randomUUID();
    const initialVersion: CanvasVersion = {
      id: crypto.randomUUID(),
      content,
      timestamp: Date.now(),
      description: 'Initial version',
    };

    const doc: CanvasDocument = {
      id,
      title,
      language,
      content,
      versions: [initialVersion],
      currentVersionId: initialVersion.id,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    const documents = new Map(get().documents);
    documents.set(id, doc);
    set({ documents, activeDocumentId: id, isOpen: true });
    return id;
  },

  getActiveDocument: () => {
    const { activeDocumentId, documents } = get();
    if (!activeDocumentId) return null;
    return documents.get(activeDocumentId) || null;
  },
}));
```

### FR-3: Canvas Panel Component

```tsx
// ui/src/components/canvas/CanvasPanel.tsx

'use client';

import { useEffect, useRef, useState } from 'react';
import { useCanvasStore } from '@/store/canvas';
import { CanvasEditor } from './CanvasEditor';
import { CanvasToolbar } from './CanvasToolbar';
import { CanvasHistory } from './CanvasHistory';
import { CanvasShortcuts } from './CanvasShortcuts';

interface CanvasPanelProps {
  onAIEdit: (instruction: string) => void;
}

export function CanvasPanel({ onAIEdit }: CanvasPanelProps) {
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
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="canvas-panel">
      <div className="canvas-header">
        <div className="canvas-title">
          <span className="canvas-icon">
            {doc.language === 'text' ? <DocIcon /> : <CodeIcon />}
          </span>
          <span>{doc.title}</span>
        </div>

        <div className="canvas-actions">
          <button onClick={() => setShowShortcuts(!showShortcuts)} title="AI Shortcuts">
            <MagicIcon />
          </button>
          <button onClick={() => setShowHistory(!showHistory)} title="Version History">
            <HistoryIcon />
          </button>
          <button onClick={handleCopy} title="Copy to Clipboard">
            <CopyIcon />
          </button>
          <button onClick={handleDownload} title="Download">
            <DownloadIcon />
          </button>
          <button onClick={closeCanvas} title="Close Canvas">
            <CloseIcon />
          </button>
        </div>
      </div>

      {showShortcuts && (
        <CanvasShortcuts
          language={doc.language}
          onSelect={(instruction) => {
            onAIEdit(instruction);
            setShowShortcuts(false);
          }}
          onClose={() => setShowShortcuts(false)}
        />
      )}

      <CanvasEditor
        content={doc.content}
        language={doc.language}
        onChange={(content) => updateContent(content, 'User edit')}
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

// Icons (simplified)
function DocIcon() {
  return <svg viewBox="0 0 24 24" className="w-4 h-4"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="none" stroke="currentColor" strokeWidth="2"/></svg>;
}
function CodeIcon() {
  return <svg viewBox="0 0 24 24" className="w-4 h-4"><path d="M16 18l6-6-6-6M8 6l-6 6 6 6" fill="none" stroke="currentColor" strokeWidth="2"/></svg>;
}
function MagicIcon() {
  return <svg viewBox="0 0 24 24" className="w-4 h-4"><path d="M15 4V2M15 16v-2M8 9h2M20 9h2M17.8 11.8L19 13M17.8 6.2L19 5M3 21l9-9" fill="none" stroke="currentColor" strokeWidth="2"/></svg>;
}
function HistoryIcon() {
  return <svg viewBox="0 0 24 24" className="w-4 h-4"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" fill="none" stroke="currentColor" strokeWidth="2"/></svg>;
}
function CopyIcon() {
  return <svg viewBox="0 0 24 24" className="w-4 h-4"><rect x="9" y="9" width="13" height="13" rx="2" fill="none" stroke="currentColor" strokeWidth="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" fill="none" stroke="currentColor" strokeWidth="2"/></svg>;
}
function DownloadIcon() {
  return <svg viewBox="0 0 24 24" className="w-4 h-4"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" fill="none" stroke="currentColor" strokeWidth="2"/></svg>;
}
function CloseIcon() {
  return <svg viewBox="0 0 24 24" className="w-4 h-4"><path d="M18 6L6 18M6 6l12 12" fill="none" stroke="currentColor" strokeWidth="2"/></svg>;
}
```

### FR-4: Canvas Editor Component

```tsx
// ui/src/components/canvas/CanvasEditor.tsx

'use client';

import { useCallback, useEffect, useRef } from 'react';
import { EditorView, basicSetup } from 'codemirror';
import { EditorState } from '@codemirror/state';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { oneDark } from '@codemirror/theme-one-dark';

interface CanvasEditorProps {
  content: string;
  language: string;
  onChange: (content: string) => void;
  readonly?: boolean;
}

const languageExtensions: Record<string, () => any> = {
  javascript: javascript,
  typescript: () => javascript({ typescript: true }),
  python: python,
  html: html,
  css: css,
  json: json,
  markdown: markdown,
  text: markdown, // Use markdown for plain text (good formatting)
};

export function CanvasEditor({
  content,
  language,
  onChange,
  readonly = false,
}: CanvasEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const contentRef = useRef(content);

  // Update content ref when prop changes
  useEffect(() => {
    contentRef.current = content;
  }, [content]);

  useEffect(() => {
    if (!containerRef.current) return;

    const langExt = languageExtensions[language] || markdown;

    const state = EditorState.create({
      doc: content,
      extensions: [
        basicSetup,
        oneDark,
        langExt(),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            const newContent = update.state.doc.toString();
            if (newContent !== contentRef.current) {
              contentRef.current = newContent;
              onChange(newContent);
            }
          }
        }),
        EditorState.readOnly.of(readonly),
        EditorView.theme({
          '&': {
            height: '100%',
            fontSize: '14px',
          },
          '.cm-scroller': {
            overflow: 'auto',
          },
        }),
      ],
    });

    const view = new EditorView({
      state,
      parent: containerRef.current,
    });

    viewRef.current = view;

    return () => {
      view.destroy();
    };
  }, [language, readonly]); // Only recreate editor when language/readonly changes

  // Update content when prop changes externally
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const currentContent = view.state.doc.toString();
    if (content !== currentContent && content !== contentRef.current) {
      view.dispatch({
        changes: {
          from: 0,
          to: currentContent.length,
          insert: content,
        },
      });
    }
  }, [content]);

  return <div ref={containerRef} className="canvas-editor" />;
}
```

### FR-5: Canvas Shortcuts Component

```tsx
// ui/src/components/canvas/CanvasShortcuts.tsx

'use client';

interface Shortcut {
  label: string;
  instruction: string;
  icon: string;
}

const CODE_SHORTCUTS: Shortcut[] = [
  { label: 'Fix Bugs', instruction: 'Fix any bugs in this code', icon: '🐛' },
  { label: 'Add Comments', instruction: 'Add helpful comments explaining the code', icon: '💬' },
  { label: 'Optimize', instruction: 'Optimize this code for better performance', icon: '⚡' },
  { label: 'Add Types', instruction: 'Add type annotations to this code', icon: '📝' },
  { label: 'Add Tests', instruction: 'Generate unit tests for this code', icon: '🧪' },
  { label: 'Simplify', instruction: 'Simplify this code while maintaining functionality', icon: '✨' },
  { label: 'Make Async', instruction: 'Convert this to async/await pattern', icon: '🔄' },
  { label: 'Add Error Handling', instruction: 'Add proper error handling', icon: '🛡️' },
];

const TEXT_SHORTCUTS: Shortcut[] = [
  { label: 'Make Shorter', instruction: 'Make this text more concise', icon: '📉' },
  { label: 'Make Longer', instruction: 'Expand and elaborate on this text', icon: '📈' },
  { label: 'Simplify', instruction: 'Simplify this text for easier understanding', icon: '✨' },
  { label: 'More Formal', instruction: 'Make this text more formal and professional', icon: '👔' },
  { label: 'More Casual', instruction: 'Make this text more casual and friendly', icon: '😊' },
  { label: 'Fix Grammar', instruction: 'Fix grammar and spelling errors', icon: '✅' },
  { label: 'Add Examples', instruction: 'Add examples to illustrate the points', icon: '💡' },
  { label: 'Summarize', instruction: 'Create a summary of this text', icon: '📋' },
];

interface CanvasShortcutsProps {
  language: string;
  onSelect: (instruction: string) => void;
  onClose: () => void;
}

export function CanvasShortcuts({ language, onSelect, onClose }: CanvasShortcutsProps) {
  const shortcuts = language === 'text' ? TEXT_SHORTCUTS : CODE_SHORTCUTS;

  return (
    <div className="canvas-shortcuts">
      <div className="canvas-shortcuts-header">
        <span>AI Shortcuts</span>
        <button onClick={onClose} className="canvas-shortcuts-close">
          ×
        </button>
      </div>
      <div className="canvas-shortcuts-grid">
        {shortcuts.map((shortcut) => (
          <button
            key={shortcut.label}
            onClick={() => onSelect(shortcut.instruction)}
            className="canvas-shortcut-btn"
          >
            <span className="canvas-shortcut-icon">{shortcut.icon}</span>
            <span>{shortcut.label}</span>
          </button>
        ))}
      </div>
      <div className="canvas-shortcuts-custom">
        <input
          type="text"
          placeholder="Or type custom instruction..."
          onKeyDown={(e) => {
            if (e.key === 'Enter' && e.currentTarget.value) {
              onSelect(e.currentTarget.value);
            }
          }}
        />
      </div>
    </div>
  );
}
```

### FR-6: Canvas History Component

```tsx
// ui/src/components/canvas/CanvasHistory.tsx

'use client';

import { useCanvasStore, type CanvasVersion } from '@/store/canvas';

interface CanvasHistoryProps {
  versions: CanvasVersion[];
  currentVersionId: string;
  onClose: () => void;
}

export function CanvasHistory({ versions, currentVersionId, onClose }: CanvasHistoryProps) {
  const { restoreVersion } = useCanvasStore();

  // Show versions in reverse chronological order
  const sortedVersions = [...versions].reverse();

  return (
    <div className="canvas-history">
      <div className="canvas-history-header">
        <span>Version History</span>
        <button onClick={onClose} className="canvas-history-close">
          ×
        </button>
      </div>
      <div className="canvas-history-list">
        {sortedVersions.map((version) => (
          <div
            key={version.id}
            className={`canvas-history-item ${version.id === currentVersionId ? 'current' : ''}`}
          >
            <div className="canvas-history-info">
              <span className="canvas-history-desc">{version.description}</span>
              <span className="canvas-history-time">
                {formatTime(version.timestamp)}
              </span>
            </div>
            {version.id !== currentVersionId && (
              <button
                onClick={() => restoreVersion(version.id)}
                className="canvas-history-restore"
              >
                Restore
              </button>
            )}
            {version.id === currentVersionId && (
              <span className="canvas-history-current-badge">Current</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}
```

### FR-7: Canvas Styles

```css
/* ui/src/app/globals.css */

/* Canvas Panel */
.canvas-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 50%;
  max-width: 800px;
  height: 100vh;
  background: var(--bg-primary);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: 100;
  animation: slideIn 0.2s ease;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

@media (max-width: 1024px) {
  .canvas-panel {
    width: 100%;
    max-width: none;
  }
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-color);
  background: var(--card-bg);
}

.canvas-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--text-primary);
}

.canvas-icon {
  color: var(--accent-green);
}

.canvas-actions {
  display: flex;
  gap: 0.25rem;
}

.canvas-actions button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background: none;
  border: none;
  border-radius: 0.375rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.canvas-actions button:hover {
  background: var(--card-bg-hover);
  color: var(--text-primary);
}

.canvas-editor {
  flex: 1;
  overflow: hidden;
}

/* Canvas Shortcuts */
.canvas-shortcuts {
  border-bottom: 1px solid var(--border-color);
  background: var(--card-bg);
}

.canvas-shortcuts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.canvas-shortcuts-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.25rem;
  cursor: pointer;
}

.canvas-shortcuts-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
  padding: 0 1rem 0.5rem;
}

@media (max-width: 640px) {
  .canvas-shortcuts-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.canvas-shortcut-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.canvas-shortcut-btn:hover {
  background: var(--card-bg-hover);
  border-color: var(--accent-green);
  color: var(--text-primary);
}

.canvas-shortcut-icon {
  font-size: 1rem;
}

.canvas-shortcuts-custom {
  padding: 0.5rem 1rem 1rem;
}

.canvas-shortcuts-custom input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: var(--input-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.canvas-shortcuts-custom input:focus {
  outline: none;
  border-color: var(--accent-green);
}

/* Canvas History */
.canvas-history {
  position: absolute;
  top: 3.5rem;
  right: 0;
  width: 280px;
  max-height: 400px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 10;
}

.canvas-history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-color);
  font-weight: 600;
  font-size: 0.875rem;
}

.canvas-history-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.25rem;
  cursor: pointer;
}

.canvas-history-list {
  max-height: 320px;
  overflow-y: auto;
}

.canvas-history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-color);
}

.canvas-history-item:last-child {
  border-bottom: none;
}

.canvas-history-item.current {
  background: var(--accent-green-bg);
}

.canvas-history-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.canvas-history-desc {
  font-size: 0.875rem;
  color: var(--text-primary);
}

.canvas-history-time {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.canvas-history-restore {
  padding: 0.25rem 0.5rem;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
}

.canvas-history-restore:hover {
  background: var(--card-bg-hover);
  color: var(--text-primary);
}

.canvas-history-current-badge {
  padding: 0.125rem 0.375rem;
  background: var(--accent-green);
  border-radius: 0.25rem;
  color: var(--bg-primary);
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
}
```

### FR-8: Integration with Chat

```tsx
// ui/src/app/chat/page.tsx

// Modify chat page to include Canvas panel

import { CanvasPanel } from '@/components/canvas/CanvasPanel';
import { useCanvasStore } from '@/store/canvas';

export default function ChatPage() {
  const { isOpen } = useCanvasStore();

  const handleAIEdit = async (instruction: string) => {
    // Send instruction to agent along with current canvas content
    const doc = useCanvasStore.getState().getActiveDocument();
    if (!doc) return;

    // Add message to chat requesting the edit
    const message = `Please edit the canvas content (${doc.title}):\n\nInstruction: ${instruction}\n\nCurrent content:\n\`\`\`${doc.language}\n${doc.content}\n\`\`\``;

    // Trigger chat send with this message
    // The agent will respond with updated :::canvas block
  };

  return (
    <div className={`chat-layout ${isOpen ? 'canvas-open' : ''}`}>
      <Sidebar />
      <ChatArea />
      {isOpen && <CanvasPanel onAIEdit={handleAIEdit} />}
    </div>
  );
}
```

### FR-9: Canvas Content Parser

```typescript
// ui/src/lib/canvas-parser.ts

import { useCanvasStore } from '@/store/canvas';

export interface CanvasBlock {
  language: string;
  title: string;
  content: string;
  readonly: boolean;
}

export function parseCanvasBlocks(content: string): CanvasBlock[] {
  const blocks: CanvasBlock[] = [];
  const regex = /:::canvas\[([^\]]*)\]\n([\s\S]*?)\n:::/g;

  let match;
  while ((match = regex.exec(content)) !== null) {
    const attributes = parseAttributes(match[1]);
    blocks.push({
      language: attributes.language || 'text',
      title: attributes.title || 'Untitled',
      content: match[2].trim(),
      readonly: attributes.readonly === 'true',
    });
  }

  return blocks;
}

function parseAttributes(attrString: string): Record<string, string> {
  const attrs: Record<string, string> = {};
  const regex = /(\w+)=([^,\]]+)/g;

  let match;
  while ((match = regex.exec(attrString)) !== null) {
    attrs[match[1]] = match[2];
  }

  return attrs;
}

export function handleCanvasContent(content: string): void {
  const blocks = parseCanvasBlocks(content);

  if (blocks.length > 0) {
    const block = blocks[0]; // Open first canvas block
    useCanvasStore.getState().createDocument(
      block.title,
      block.language,
      block.content
    );
  }
}
```

## Non-Functional Requirements

### NFR-1: Performance

- Editor responsive with files up to 10,000 lines
- Syntax highlighting without lag
- Version history stored efficiently (diff-based storage optional)

### NFR-2: Persistence

- Canvas state persists across page refreshes (localStorage)
- Version history maintained for session duration

### NFR-3: Mobile

- Responsive panel (full-width on mobile)
- Touch-friendly controls
- Keyboard accessible

## Acceptance Criteria

- [ ] Canvas panel opens when agent sends :::canvas block
- [ ] Code editor with syntax highlighting working
- [ ] Text editor for documents working
- [ ] Direct editing updates content
- [ ] AI shortcuts trigger agent edits
- [ ] Version history shows all changes
- [ ] Restore version functionality working
- [ ] Copy and download working
- [ ] Panel closes properly
- [ ] Mobile responsive layout

## Files to Modify/Create

```
ui/
└── src/
    ├── components/
    │   └── canvas/
    │       ├── CanvasPanel.tsx       # NEW - Main panel
    │       ├── CanvasEditor.tsx      # NEW - CodeMirror editor
    │       ├── CanvasShortcuts.tsx   # NEW - AI shortcuts
    │       ├── CanvasHistory.tsx     # NEW - Version history
    │       └── index.ts              # NEW - Exports
    ├── store/
    │   └── canvas.ts                 # NEW - Canvas state
    ├── lib/
    │   └── canvas-parser.ts          # NEW - Content parser
    └── app/
        ├── chat/
        │   └── page.tsx              # MODIFY - Add Canvas
        └── globals.css               # MODIFY - Canvas styles
```

## Dependencies

```json
// ui/package.json
{
  "codemirror": "^6.0.0",
  "@codemirror/lang-javascript": "^6.2.0",
  "@codemirror/lang-python": "^6.1.0",
  "@codemirror/lang-html": "^6.4.0",
  "@codemirror/lang-css": "^6.2.0",
  "@codemirror/lang-json": "^6.0.0",
  "@codemirror/lang-markdown": "^6.2.0",
  "@codemirror/theme-one-dark": "^6.1.0"
}
```

## Related Specs

- `specs/48_rich_data_visualization.md` - Visualizations in canvas
- `specs/11_chat_ui.md` - Chat UI integration
- `specs/41_enhanced_agent_system_prompt.md` - Agent capabilities
