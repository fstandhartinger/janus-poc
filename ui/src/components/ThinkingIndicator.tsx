'use client';

interface ThinkingIndicatorProps {
  isVisible: boolean;
  message?: string;
}

export function ThinkingIndicator({ isVisible, message }: ThinkingIndicatorProps) {
  if (!isVisible) return null;

  return (
    <div className="thinking-indicator">
      <div className="typing-indicator" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <span>{message || 'Thinking...'}</span>
    </div>
  );
}
