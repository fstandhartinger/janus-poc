import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { Message } from '@/types/chat';

vi.mock('@/hooks/useArena', () => ({
  useArena: () => ({
    submitVote: vi.fn(),
  }),
}));

vi.mock('@/store/chat', () => ({
  useChatStore: (selector: (state: { updateMessage: () => void }) => unknown) =>
    selector({ updateMessage: vi.fn() }),
}));

vi.mock('./chat/MessageFooter', () => ({
  MessageFooter: () => null,
}));

vi.mock('./chat/MessageActions', () => ({
  MessageActions: () => null,
}));

vi.mock('./ThinkingIndicator', () => ({
  ThinkingIndicator: () => null,
}));

describe('MessageBubble artifacts', () => {
  it('renders audio/video players and file attachments from artifacts', async () => {
    const { MessageBubble } = await import('./MessageBubble');
    const message: Message = {
      id: 'msg_1',
      role: 'assistant',
      content: '',
      artifacts: [
        {
          id: 'art_audio',
          type: 'binary',
          mime_type: 'audio/wav',
          display_name: 'voice.wav',
          size_bytes: 1024,
          created_at: new Date().toISOString(),
          ttl_seconds: 3600,
          url: '/api/artifacts/chat_1/voice.wav',
        },
        {
          id: 'art_video',
          type: 'binary',
          mime_type: 'video/mp4',
          display_name: 'clip.mp4',
          size_bytes: 2048,
          created_at: new Date().toISOString(),
          ttl_seconds: 3600,
          url: 'https://example.com/clip.mp4',
        },
        {
          id: 'art_file',
          type: 'file',
          mime_type: 'application/pdf',
          display_name: 'report.pdf',
          size_bytes: 123,
          created_at: new Date().toISOString(),
          ttl_seconds: 3600,
          url: '/api/artifacts/chat_1/report.pdf',
        },
      ],
      created_at: new Date(),
    };

    const { container } = render(
      React.createElement(MessageBubble, {
        message,
        showReasoning: false,
        isStreaming: false,
      })
    );

    expect(screen.getByText('Attachment')).toBeInTheDocument();
    expect(screen.getByText('report.pdf')).toBeInTheDocument();

    const attachmentLink = screen.getByRole('link', { name: /report\.pdf/i });
    expect(attachmentLink).toHaveAttribute('href', '/api/artifacts/chat_1/report.pdf');
    expect(attachmentLink).not.toHaveAttribute('target');

    // Audio artifact is rendered via AudioResponse -> AudioPlayer
    expect(screen.getByLabelText('Download audio')).toBeInTheDocument();
    expect(container.querySelector('audio')).toBeTruthy();

    // Video artifact renders an inline player + download link.
    expect(container.querySelector('video')).toBeTruthy();
    const videoDownload = screen.getByRole('link', { name: 'Download' });
    expect(videoDownload).toHaveAttribute('href', 'https://example.com/clip.mp4');
    expect(videoDownload).toHaveAttribute('target', '_blank');
  });
});
