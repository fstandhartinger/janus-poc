'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Maximize2, Minimize2, RefreshCw } from 'lucide-react';

interface GenerativeUIProps {
  html: string;
  className?: string;
}

const RESIZE_MESSAGE_TYPE = 'janus-gen-ui-resize';
const RESIZE_SCRIPT_MARKER = 'data-janus-gen-ui-resize';
const DEFAULT_HEIGHT = 300;
const MIN_HEIGHT = 200;
const MAX_HEIGHT = 500;
const TOOLBAR_HEIGHT = 45;

const RESIZE_SCRIPT = `<script ${RESIZE_SCRIPT_MARKER}>
(function () {
  function sendHeight() {
    try {
      var body = document.body;
      var doc = document.documentElement;
      var height = body ? body.scrollHeight : (doc ? doc.scrollHeight : 0);
      window.parent.postMessage({ type: '${RESIZE_MESSAGE_TYPE}', height: height }, '*');
    } catch (error) {
      // Ignore resize errors inside sandboxed frame.
    }
  }

  function schedule() {
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(sendHeight);
    } else {
      setTimeout(sendHeight, 0);
    }
  }

  window.addEventListener('load', schedule);
  window.addEventListener('resize', schedule);

  if (window.ResizeObserver && document.body) {
    var observer = new ResizeObserver(schedule);
    observer.observe(document.body);
  }

  setTimeout(schedule, 50);
})();
</script>`;

function injectResizeScript(html: string): string {
  if (!html || html.includes(RESIZE_SCRIPT_MARKER)) {
    return html;
  }

  if (html.includes('</body>')) {
    return html.replace(/<\/body>/i, `${RESIZE_SCRIPT}</body>`);
  }

  if (html.includes('</html>')) {
    return html.replace(/<\/html>/i, `${RESIZE_SCRIPT}</html>`);
  }

  return `${html}\n${RESIZE_SCRIPT}`;
}

function clampHeight(height: number, maxHeight: number) {
  const padded = height + 20;
  return Math.max(MIN_HEIGHT, Math.min(padded, maxHeight));
}

export function GenerativeUI({ html, className }: GenerativeUIProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);
  const [contentHeight, setContentHeight] = useState(DEFAULT_HEIGHT);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const srcDoc = useMemo(() => injectResizeScript(html), [html]);

  // Reset content height when iframe/html changes
  useEffect(() => {
    // Schedule state update outside effect render cycle
    queueMicrotask(() => {
      setContentHeight(DEFAULT_HEIGHT);
    });
  }, [iframeKey, html]);

  useEffect(() => {
    if (!isFullscreen) {
      return;
    }

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [isFullscreen]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isFullscreen]);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) {
      return;
    }

    const handleMessage = (event: MessageEvent) => {
      if (event.source !== iframe.contentWindow) {
        return;
      }
      const data = event.data as { type?: string; height?: number } | null;
      if (!data || data.type !== RESIZE_MESSAGE_TYPE || typeof data.height !== 'number') {
        return;
      }

      const maxHeight = isFullscreen ? window.innerHeight - 60 : MAX_HEIGHT;
      setContentHeight(clampHeight(data.height, maxHeight));
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [iframeKey, isFullscreen]);

  const handleRefresh = () => setIframeKey((prev) => prev + 1);
  const toggleFullscreen = () => setIsFullscreen((prev) => !prev);

  const containerClasses = isFullscreen
    ? 'fixed inset-0 z-50 bg-[#0B0F14] flex flex-col'
    : `relative rounded-lg border border-white/10 overflow-hidden ${className || ''}`;

  return (
    <div className={containerClasses}>
      <div className="flex items-center justify-between px-3 py-2 bg-white/5 border-b border-white/10">
        <span className="text-xs text-white/60 font-mono hidden sm:inline">Interactive UI</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            className="p-1 hover:bg-white/10 rounded"
            title="Refresh"
            aria-label="Refresh interactive UI"
          >
            <RefreshCw size={14} className="text-white/60" />
          </button>
          <button
            type="button"
            onClick={toggleFullscreen}
            className="p-1 hover:bg-white/10 rounded"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? (
              <Minimize2 size={14} className="text-white/60" />
            ) : (
              <Maximize2 size={14} className="text-white/60" />
            )}
          </button>
        </div>
      </div>

      <iframe
        key={iframeKey}
        ref={iframeRef}
        srcDoc={srcDoc}
        sandbox="allow-scripts"
        className="w-full bg-transparent"
        style={{
          minHeight: `${MIN_HEIGHT}px`,
          height: isFullscreen ? `calc(100vh - ${TOOLBAR_HEIGHT}px)` : `${contentHeight}px`,
          border: 'none',
        }}
        title="Generative UI"
      />
    </div>
  );
}
