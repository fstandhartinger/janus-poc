'use client';

import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { FilePreview } from './FilePreview';
import { MicrophonePermissionBanner } from './MicrophonePermissionDialog';
import { VoiceInputButton } from './VoiceInputButton';
import { PlusMenu } from './chat/PlusMenu';
import { SelectedTags } from './chat/SelectedTags';
import {
  ALL_ACCEPT_TYPES,
  MAX_FILES_PER_MESSAGE,
  MAX_TOTAL_SIZE,
  SUPPORTED_FILE_TYPES,
  type AttachedFile,
} from '@/lib/file-types';
import { detectFileCategory, formatBytes } from '@/lib/file-utils';
import { processFile } from '@/lib/file-processor';
import type { GenerationFlags, GenerationTag } from '@/types/generation';

interface ChatInputProps {
  onSend: (content: string, files: AttachedFile[], generationFlags?: GenerationFlags) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [selectedTags, setSelectedTags] = useState<GenerationTag[]>([]);
  const [statusMessage, setStatusMessage] = useState<{ type: 'error' | 'info'; text: string } | null>(
    null
  );
  const [processingFiles, setProcessingFiles] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const voiceInputEnabled = process.env.NEXT_PUBLIC_ENABLE_VOICE_INPUT === 'true';

  const handleTranscription = useCallback((text: string) => {
    setInput((prev) => {
      const separator = prev.trim() ? ' ' : '';
      return prev + separator + text;
    });
    textareaRef.current?.focus();
  }, []);

  // Auto-resize textarea based on content
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';
    // Set to scrollHeight (content height)
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, []);

  // Adjust height when input changes
  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  const buildGenerationFlags = useCallback((tags: GenerationTag[]): GenerationFlags | undefined => {
    if (tags.length === 0) return undefined;
    return {
      generate_image: tags.includes('generate_image'),
      generate_video: tags.includes('generate_video'),
      generate_audio: tags.includes('generate_audio'),
      deep_research: tags.includes('deep_research'),
      web_search: tags.includes('web_search'),
    };
  }, []);

  const submitMessage = useCallback(() => {
    if (!input.trim() && attachedFiles.length === 0) return;
    const generationFlags = buildGenerationFlags(selectedTags);
    onSend(input.trim(), attachedFiles, generationFlags);
    setInput('');
    setAttachedFiles([]);
    setSelectedTags([]);
    setStatusMessage(null);
    setProcessingFiles([]);
  }, [attachedFiles, buildGenerationFlags, input, onSend, selectedTags]);

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

  const handleFileSelect = async (fileList: FileList) => {
    const selectedFiles = Array.from(fileList);
    if (selectedFiles.length === 0) return;

    setStatusMessage(null);

    const remainingSlots = MAX_FILES_PER_MESSAGE - attachedFiles.length;
    if (remainingSlots <= 0) {
      setStatusMessage({ type: 'error', text: `Maximum ${MAX_FILES_PER_MESSAGE} files per message` });
      return;
    }

    const filesToProcess = selectedFiles.slice(0, remainingSlots);
    if (selectedFiles.length > remainingSlots) {
      setStatusMessage({ type: 'error', text: `Maximum ${MAX_FILES_PER_MESSAGE} files per message` });
    }

    let totalSize = attachedFiles.reduce((sum, file) => sum + file.size, 0);

    for (const file of filesToProcess) {
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

  };

  const removeFile = (id: string) => {
    setAttachedFiles((prev) => prev.filter((file) => file.id !== id));
  };

  const toggleTag = (tag: GenerationTag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag]
    );
  };

  const removeTag = (tag: GenerationTag) => {
    setSelectedTags((prev) => prev.filter((item) => item !== tag));
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

      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {attachedFiles.map((file) => (
            <FilePreview key={file.id} file={file} onRemove={() => removeFile(file.id)} disabled={disabled} />
          ))}
        </div>
      )}

      <div className="chat-input-container">
        <PlusMenu
          onFileSelect={handleFileSelect}
          selectedTags={selectedTags}
          onTagToggle={toggleTag}
          disabled={disabled}
          accept={ALL_ACCEPT_TYPES}
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

      <SelectedTags tags={selectedTags} onRemove={removeTag} disabled={disabled} />
    </form>
  );
}
