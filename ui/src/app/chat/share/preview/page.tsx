'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function ShareTargetPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [content, setContent] = useState<{ title?: string; text?: string; url?: string } | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const title = searchParams.get('title') || undefined;
    const text = searchParams.get('text') || undefined;
    const url = searchParams.get('url') || undefined;

    if (title || text || url) {
      setContent({ title, text, url });
    }
  }, [searchParams]);

  const handleChat = () => {
    if (!content) return;
    let message = '';
    if (content.title) message += `${content.title}\n\n`;
    if (content.text) message += `${content.text}\n\n`;
    if (content.url) message += content.url;

    const params = new URLSearchParams({
      initial: message.trim(),
      source: 'share',
    });
    router.push(`/chat?${params.toString()}`);
  };

  const handleReadToMe = () => {
    if (!content) return;
    setIsProcessing(true);

    if (content.url && !content.text) {
      const instruction = `Please visit this URL, extract the main content, create a transcript suitable for reading aloud, and then read it to me: ${content.url}`;
      const params = new URLSearchParams({
        initial: instruction,
        autoSubmit: 'true',
        tts: 'true',
        source: 'share',
      });
      router.push(`/chat?${params.toString()}`);
      return;
    }

    const textToRead = content.text ? content.text : content.title || '';
    if (textToRead) {
      const params = new URLSearchParams({
        initial: `Read the following text to me:\n\n${textToRead}`,
        autoSubmit: 'true',
        tts: 'true',
        source: 'share',
      });
      router.push(`/chat?${params.toString()}`);
    }
  };

  if (!content) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="glass-card p-6 rounded-xl max-w-md w-full text-center">
          <p className="text-white/60">No content received to share.</p>
          <button
            onClick={() => router.push('/chat')}
            className="mt-4 px-6 py-2 bg-moss text-black rounded-lg font-medium"
          >
            Go to Chat
          </button>
        </div>
      </div>
    );
  }

  if (isProcessing) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="glass-card p-6 rounded-xl max-w-md w-full text-center">
          <div className="w-8 h-8 border-2 border-moss border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-white/60 mt-4">Processing...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="glass-card p-6 rounded-xl max-w-md w-full">
        <h1 className="text-xl font-semibold text-white mb-4">Share with Janus</h1>

        <div className="bg-white/5 rounded-lg p-4 mb-6 max-h-40 overflow-y-auto">
          {content.title && (
            <p className="text-white font-medium text-sm mb-1">{content.title}</p>
          )}
          {content.text && (
            <p className="text-white/70 text-sm line-clamp-4">{content.text}</p>
          )}
          {content.url && (
            <p className="text-moss text-sm truncate mt-1">{content.url}</p>
          )}
        </div>

        <div className="space-y-3">
          <button
            onClick={handleChat}
            className="w-full p-4 bg-moss/20 hover:bg-moss/30 border border-moss/30 rounded-xl text-left transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-moss/30 flex items-center justify-center">
                <svg className="w-5 h-5 text-moss" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">Use in Chat</p>
                <p className="text-white/60 text-sm">Insert content into new chat</p>
              </div>
            </div>
          </button>

          <button
            onClick={handleReadToMe}
            className="w-full p-4 bg-moss/20 hover:bg-moss/30 border border-moss/30 rounded-xl text-left transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-moss/30 flex items-center justify-center">
                <svg className="w-5 h-5 text-moss" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"
                  />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">Read to Me</p>
                <p className="text-white/60 text-sm">
                  {content.url ? 'Visit page and read aloud' : 'Convert text to speech'}
                </p>
              </div>
            </div>
          </button>
        </div>

        <button
          onClick={() => router.push('/chat')}
          className="w-full mt-4 py-2 text-white/60 hover:text-white text-sm transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
