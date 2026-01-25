'use client';

import { useCallback, useRef, useState, type FormEvent, type ChangeEvent, type KeyboardEvent } from 'react';
import { FilePreview } from './FilePreview';
import { MicrophonePermissionBanner } from './MicrophonePermissionDialog';
import { VoiceInputButton } from './VoiceInputButton';
import {
  ALL_ACCEPT_TYPES,
  MAX_FILES_PER_MESSAGE,
  MAX_TOTAL_SIZE,
  SUPPORTED_FILE_TYPES,
  type AttachedFile,
} from '@/lib/file-types';
import { detectFileCategory, formatBytes } from '@/lib/file-utils';
import { processFile } from '@/lib/file-processor';

interface ChatInputProps {
  onSend: (
    content: string,
    files: AttachedFile[],
    options?: { deepResearch?: boolean; researchMode?: 'light' | 'max' }
  ) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [deepResearchEnabled, setDeepResearchEnabled] = useState(false);
  const [researchMode, setResearchMode] = useState<'light' | 'max'>('light');
  const [statusMessage, setStatusMessage] = useState<{ type: 'error' | 'info'; text: string } | null>(
    null
  );
  const [processingFiles, setProcessingFiles] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const voiceInputEnabled = process.env.NEXT_PUBLIC_ENABLE_VOICE_INPUT === 'true';

  const handleTranscription = useCallback((text: string) => {
    setInput((prev) => {
      const separator = prev.trim() ? ' ' : '';
      return prev + separator + text;
    });
    textareaRef.current?.focus();
  }, []);

  const submitMessage = useCallback(() => {
    if (!input.trim() && attachedFiles.length === 0) return;
    onSend(
      input.trim(),
      attachedFiles,
      deepResearchEnabled ? { deepResearch: true, researchMode } : undefined
    );
    setInput('');
    setAttachedFiles([]);
    setStatusMessage(null);
    setProcessingFiles([]);
  }, [attachedFiles, deepResearchEnabled, input, onSend, researchMode]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submitMessage();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitMessage();
    }
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length === 0) return;

    setStatusMessage(null);

    const remainingSlots = MAX_FILES_PER_MESSAGE - attachedFiles.length;
    if (remainingSlots <= 0) {
      setStatusMessage({ type: 'error', text: `Maximum ${MAX_FILES_PER_MESSAGE} files per message` });
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    const files = selectedFiles.slice(0, remainingSlots);
    if (selectedFiles.length > remainingSlots) {
      setStatusMessage({ type: 'error', text: `Maximum ${MAX_FILES_PER_MESSAGE} files per message` });
    }

    let totalSize = attachedFiles.reduce((sum, file) => sum + file.size, 0);

    for (const file of files) {
      const category = detectFileCategory(file);
      if (!category) {
        setStatusMessage({ type: 'error', text: `Unsupported file type: ${file.name}` });
        continue;
      }

      const typeConfig = SUPPORTED_FILE_TYPES[category];
      if (file.size > typeConfig.maxSize) {
        setStatusMessage({
          type: 'error',
          text: `${file.name} exceeds ${formatBytes(typeConfig.maxSize)} limit`,
        });
        continue;
      }

      if (totalSize + file.size > MAX_TOTAL_SIZE) {
        setStatusMessage({
          type: 'error',
          text: `Total attachment size exceeds ${formatBytes(MAX_TOTAL_SIZE)} limit`,
        });
        continue;
      }

      totalSize += file.size;
      const isLarge = file.size > 10 * 1024 * 1024;
      if (isLarge) {
        setProcessingFiles((prev) => [...prev, file.name]);
      }

      try {
        const processed = await processFile(file, category);
        setAttachedFiles((prev) => [...prev, processed]);
      } catch {
        setStatusMessage({ type: 'error', text: `Failed to process ${file.name}` });
      } finally {
        if (isLarge) {
          setProcessingFiles((prev) => prev.filter((name) => name !== file.name));
        }
      }
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (id: string) => {
    setAttachedFiles((prev) => prev.filter((file) => file.id !== id));
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-wrapper">
      {voiceInputEnabled && <MicrophonePermissionBanner />}

      {statusMessage && (
        <div
          className={`mb-2 text-xs ${
            statusMessage.type === 'error' ? 'text-[#F87171]' : 'text-[#63D297]'
          }`}
          role="status"
          aria-live="polite"
        >
          {statusMessage.text}
        </div>
      )}

      {processingFiles.length > 0 && (
        <div className="mb-2 text-xs text-[#9CA3AF]" aria-live="polite">
          Processing {processingFiles.join(', ')}...
        </div>
      )}

      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
        <button
          type="button"
          onClick={() => setDeepResearchEnabled((current) => !current)}
          disabled={disabled}
          aria-pressed={deepResearchEnabled}
          className={`rounded-full border px-3 py-1 transition-colors ${
            deepResearchEnabled
              ? 'border-moss/40 bg-moss/10 text-moss'
              : 'border-ink-700 text-ink-400 hover:border-ink-500 hover:text-ink-200'
          }`}
        >
          Deep research
        </button>
        {deepResearchEnabled && (
          <label className="flex items-center gap-2 text-ink-400">
            Mode
            <select
              value={researchMode}
              onChange={(event) => setResearchMode(event.target.value as 'light' | 'max')}
              className="rounded-full border border-ink-700 bg-ink-800/70 px-2 py-1 text-ink-200"
            >
              <option value="light">light</option>
              <option value="max">max</option>
            </select>
          </label>
        )}
      </div>

      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {attachedFiles.map((file) => (
            <FilePreview key={file.id} file={file} onRemove={() => removeFile(file.id)} disabled={disabled} />
          ))}
        </div>
      )}

      <div className="chat-input-container">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="w-9 h-9 rounded-full border border-[#1F2937] flex items-center justify-center text-[#9CA3AF] hover:text-[#F3F4F6] hover:border-[#374151] transition-colors disabled:opacity-50"
          aria-label="Attach files"
          title="Attach files"
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept={ALL_ACCEPT_TYPES}
          multiple
          onChange={handleFileChange}
          disabled={disabled}
          className="hidden"
          data-testid="file-input"
        />

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything..."
          disabled={disabled}
          rows={1}
          className="chat-input"
          data-testid="chat-input"
        />

        {voiceInputEnabled && (
          <VoiceInputButton onTranscription={handleTranscription} disabled={disabled} />
        )}

        <button
          type="submit"
          disabled={disabled || (!input.trim() && attachedFiles.length === 0)}
          className="chat-send-btn disabled:cursor-not-allowed"
          data-testid="send-button"
          aria-label="Send message"
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 12h16M14 6l6 6-6 6" />
          </svg>
        </button>
      </div>
    </form>
  );
}
