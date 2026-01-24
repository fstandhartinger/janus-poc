'use client';

import { useState } from 'react';
import type { ScreenshotData } from '@/types/chat';

interface ScreenshotStreamProps {
  screenshots: ScreenshotData[];
  isLive: boolean;
}

export function ScreenshotStream({ screenshots, isLive }: ScreenshotStreamProps) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (screenshots.length === 0) return null;

  const latestScreenshot = screenshots[screenshots.length - 1];

  return (
    <div className="space-y-3 mb-6">
      {isLive && (
        <div className="flex items-center gap-2 text-sm text-moss">
          <span className="w-2 h-2 bg-moss rounded-full animate-pulse" />
          Browser session active
        </div>
      )}

      <div className="relative rounded-lg overflow-hidden border border-ink-700">
        <img
          src={`data:image/png;base64,${latestScreenshot.image_base64}`}
          alt={latestScreenshot.title || 'Browser screenshot'}
          className="w-full"
        />

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
          <div className="flex items-center justify-between">
            <div className="text-sm text-white truncate max-w-[80%]">
              {latestScreenshot.url || 'Current page'}
            </div>
            <button
              onClick={() => setExpanded(screenshots.length - 1)}
              className="p-1 rounded hover:bg-white/20"
              type="button"
              aria-label="Expand screenshot"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5M3 3l7 7M21 3l-7 7M3 21l7-7M21 21l-7-7" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {screenshots.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {screenshots.map((shot, index) => (
            <button
              key={`${shot.timestamp}-${index}`}
              onClick={() => setExpanded(index)}
              className={`shrink-0 w-20 h-12 rounded overflow-hidden border-2 ${
                index === screenshots.length - 1 ? 'border-moss' : 'border-ink-700'
              }`}
              type="button"
              aria-label={`View screenshot ${index + 1}`}
            >
              <img
                src={`data:image/png;base64,${shot.image_base64}`}
                alt={`Step ${index + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
          ))}
        </div>
      )}

      {expanded !== null && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setExpanded(null)}
        >
          <div className="max-w-[90vw] max-h-[90vh]">
            <img
              src={`data:image/png;base64,${screenshots[expanded].image_base64}`}
              alt={screenshots[expanded].title || 'Browser screenshot'}
              className="max-w-full max-h-full object-contain"
            />
            <div className="text-center mt-2 text-white text-sm">
              {screenshots[expanded].url}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
