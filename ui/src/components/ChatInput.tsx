'use client';

import { useState, useRef, type FormEvent, type ChangeEvent } from 'react';
import { FilePreview } from './FilePreview';
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
  onSend: (content: string, files: AttachedFile[]) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [statusMessage, setStatusMessage] = useState<{ type: 'error' | 'info'; text: string } | null>(
    null
  );
  const [processingFiles, setProcessingFiles] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() || attachedFiles.length > 0) {
      onSend(input.trim(), attachedFiles);
      setInput('');
      setAttachedFiles([]);
      setStatusMessage(null);
      setProcessingFiles([]);
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
          className="hidden"
          data-testid="file-input"
        />

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="Ask anything..."
          disabled={disabled}
          rows={1}
          className="chat-input"
          data-testid="chat-input"
        />

        <button
          type="button"
          disabled={disabled}
          className="w-9 h-9 rounded-full border border-[#1F2937] flex items-center justify-center text-[#9CA3AF] hover:text-[#F3F4F6] hover:border-[#374151] transition-colors disabled:opacity-50"
          aria-label="Voice input"
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 3a3 3 0 00-3 3v6a3 3 0 006 0V6a3 3 0 00-3-3z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 11a7 7 0 0014 0" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v3" />
          </svg>
        </button>

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
