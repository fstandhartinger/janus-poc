'use client';

import { useState, useRef, type FormEvent, type ChangeEvent } from 'react';

interface ChatInputProps {
  onSend: (content: string, images: string[]) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [images, setImages] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() || images.length > 0) {
      onSend(input.trim(), images);
      setInput('');
      setImages([]);
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    Array.from(files).forEach((file) => {
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          const dataUrl = event.target?.result as string;
          setImages((prev) => [...prev, dataUrl]);
        };
        reader.readAsDataURL(file);
      }
    });

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-wrapper">
      {/* Image previews */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {images.map((img, i) => (
            <div key={i} className="relative group">
              <img
                src={img}
                alt="Upload preview"
                className="w-16 h-16 object-cover rounded-lg border border-[#1F2937]"
              />
              <button
                type="button"
                onClick={() => removeImage(i)}
                className="absolute -top-1 -right-1 w-5 h-5 bg-[#FA5D19] text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="chat-input-container">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="w-9 h-9 rounded-full border border-[#1F2937] flex items-center justify-center text-[#9CA3AF] hover:text-[#F3F4F6] hover:border-[#374151] transition-colors disabled:opacity-50"
          aria-label="Attach image"
          title="Attach image"
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
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
          disabled={disabled || (!input.trim() && images.length === 0)}
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
