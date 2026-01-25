# Spec 85: PWA Mobile Installation with Share Target

## Status: DRAFT

## Context / Why

The Janus Chat app should be offered as an installable Progressive Web App (PWA) on mobile devices. This enables:

1. **Faster access** - App icon on home screen
2. **Native app experience** - Fullscreen without browser UI
3. **Share Target integration** - Send texts and URLs directly to Janus
4. **Read-to-me feature** - Have content read aloud via TTS

**Critical:** The PWA must always auto-update to the latest version to avoid the common problem of stale local versions that never receive updates.

## Goals

- Offer PWA only on mobile (not desktop)
- Smart install toast with timing logic
- Reliable auto-update mechanism
- Share Target with two modes: Chat and Read-to-me
- Extract and read URL content aloud

## Non-Goals

- Desktop PWA installation
- Offline functionality (app requires internet)
- Push notifications

## Functional Requirements

### FR-1: PWA Manifest

```json
// ui/public/manifest.json
{
  "name": "Janus Chat",
  "short_name": "Janus",
  "description": "AI Chat powered by Janus",
  "start_url": "/chat?source=pwa",
  "display": "standalone",
  "background_color": "#0a0a0a",
  "theme_color": "#63D297",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "share_target": {
    "action": "/chat/share",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {
      "title": "title",
      "text": "text",
      "url": "url"
    }
  },
  "shortcuts": [
    {
      "name": "New Chat",
      "short_name": "Chat",
      "url": "/chat?new=true&source=pwa",
      "icons": [{ "src": "/icons/chat-icon.png", "sizes": "96x96" }]
    },
    {
      "name": "Read to Me",
      "short_name": "Read",
      "url": "/chat/read-to-me?source=pwa",
      "icons": [{ "src": "/icons/speaker-icon.png", "sizes": "96x96" }]
    }
  ]
}
```

### FR-2: Service Worker with Auto-Update

```typescript
// ui/public/sw.js

const CACHE_VERSION = 'v1';
const CACHE_NAME = `janus-cache-${CACHE_VERSION}`;

// Minimal caching - just the shell, content always from network
const SHELL_ASSETS = [
  '/chat',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// Install: cache shell assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  // Skip waiting to activate immediately
  self.skipWaiting();

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(SHELL_ASSETS);
    })
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          })
      );
    }).then(() => {
      // Take control immediately
      return self.clients.claim();
    })
  );
});

// Fetch: Network-first strategy (always get fresh content)
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Always use network for API calls
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/v1')) {
    return;
  }

  // Network-first for everything else
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful responses for shell assets only
        if (response.ok && SHELL_ASSETS.includes(url.pathname)) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Fallback to cache only if network fails
        return caches.match(event.request);
      })
  );
});

// Listen for update messages from the app
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
```

### FR-3: PWA Update Hook

```typescript
// ui/src/hooks/usePWAUpdate.ts

import { useEffect, useState, useCallback } from 'react';

interface UpdateState {
  updateAvailable: boolean;
  registration: ServiceWorkerRegistration | null;
}

export function usePWAUpdate() {
  const [state, setState] = useState<UpdateState>({
    updateAvailable: false,
    registration: null,
  });

  const applyUpdate = useCallback(() => {
    if (state.registration?.waiting) {
      // Tell service worker to skip waiting
      state.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      // Reload to get new version
      window.location.reload();
    }
  }, [state.registration]);

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    const registerSW = async () => {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          updateViaCache: 'none', // Always check for updates
        });

        // Check for updates on registration
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // New version available
                setState({ updateAvailable: true, registration });
              }
            });
          }
        });

        // Check for updates periodically (every 5 minutes)
        setInterval(() => {
          registration.update();
        }, 5 * 60 * 1000);

        // Check for updates on visibility change (when app comes to foreground)
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'visible') {
            registration.update();
          }
        });

        // If there's already a waiting worker, update is available
        if (registration.waiting) {
          setState({ updateAvailable: true, registration });
        }
      } catch (error) {
        console.error('[PWA] Service worker registration failed:', error);
      }
    };

    registerSW();

    // Listen for controller change (new SW activated)
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      window.location.reload();
    });
  }, []);

  return {
    updateAvailable: state.updateAvailable,
    applyUpdate,
  };
}
```

### FR-4: PWA Install Prompt Hook

```typescript
// ui/src/hooks/usePWAInstall.ts

import { useEffect, useState, useCallback } from 'react';

const STORAGE_KEY = 'pwa_install_prompt';

interface PromptState {
  dismissed: boolean;
  dismissedAt: number | null;
  dismissCount: number;
}

function getPromptState(): PromptState {
  if (typeof window === 'undefined') {
    return { dismissed: false, dismissedAt: null, dismissCount: 0 };
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {}
  return { dismissed: false, dismissedAt: null, dismissCount: 0 };
}

function savePromptState(state: PromptState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function shouldShowPrompt(): boolean {
  const state = getPromptState();

  if (!state.dismissed || !state.dismissedAt) {
    return true;
  }

  const now = Date.now();
  const daysSinceDismiss = (now - state.dismissedAt) / (1000 * 60 * 60 * 24);

  // First dismissal: wait 2 days
  if (state.dismissCount === 1) {
    return daysSinceDismiss >= 2;
  }

  // Subsequent dismissals: wait 7 days
  return daysSinceDismiss >= 7;
}

export function usePWAInstall() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [canInstall, setCanInstall] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);

  // Check if running as PWA
  const isPWA = useCallback(() => {
    if (typeof window === 'undefined') return false;

    // Check display-mode
    if (window.matchMedia('(display-mode: standalone)').matches) return true;

    // Check iOS standalone
    if ((window.navigator as any).standalone === true) return true;

    // Check URL parameter (set in manifest start_url)
    if (new URLSearchParams(window.location.search).get('source') === 'pwa') return true;

    return false;
  }, []);

  // Check if mobile
  const isMobile = useCallback(() => {
    if (typeof window === 'undefined') return false;
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    );
  }, []);

  const install = useCallback(async () => {
    if (!deferredPrompt) return false;

    try {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      setDeferredPrompt(null);

      if (outcome === 'accepted') {
        setCanInstall(false);
        setIsInstalled(true);
        return true;
      }
      return false;
    } catch (error) {
      console.error('[PWA] Install failed:', error);
      return false;
    }
  }, [deferredPrompt]);

  const dismiss = useCallback(() => {
    const state = getPromptState();
    savePromptState({
      dismissed: true,
      dismissedAt: Date.now(),
      dismissCount: state.dismissCount + 1,
    });
    setShowPrompt(false);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Don't show on desktop
    if (!isMobile()) return;

    // Don't show if already PWA
    if (isPWA()) {
      setIsInstalled(true);
      return;
    }

    // Listen for beforeinstallprompt
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setCanInstall(true);

      // Check if we should show the prompt
      if (shouldShowPrompt()) {
        setShowPrompt(true);
      }
    };

    window.addEventListener('beforeinstallprompt', handler);

    // Listen for app installed
    window.addEventListener('appinstalled', () => {
      setIsInstalled(true);
      setCanInstall(false);
      setShowPrompt(false);
    });

    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
    };
  }, [isMobile, isPWA]);

  return {
    canInstall,
    isInstalled,
    showPrompt,
    install,
    dismiss,
    isPWA: isPWA(),
    isMobile: isMobile(),
  };
}
```

### FR-5: Install Toast Component

```typescript
// ui/src/components/PWAInstallToast.tsx

'use client';

import { usePWAInstall } from '@/hooks/usePWAInstall';
import { usePWAUpdate } from '@/hooks/usePWAUpdate';
import { X, Download, RefreshCw } from 'lucide-react';

export function PWAInstallToast() {
  const { showPrompt, install, dismiss, canInstall } = usePWAInstall();
  const { updateAvailable, applyUpdate } = usePWAUpdate();

  // Show update banner if available (priority over install)
  if (updateAvailable) {
    return (
      <div className="fixed bottom-4 left-4 right-4 z-50 md:hidden">
        <div className="glass-card p-4 rounded-xl border border-moss/30 shadow-lg flex items-center gap-3">
          <RefreshCw className="w-6 h-6 text-moss shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white">Update available</p>
            <p className="text-xs text-white/60">Load new version now</p>
          </div>
          <button
            onClick={applyUpdate}
            className="px-4 py-2 bg-moss text-black text-sm font-medium rounded-lg hover:bg-moss/90 transition-colors"
          >
            Update
          </button>
        </div>
      </div>
    );
  }

  // Show install prompt
  if (!showPrompt || !canInstall) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 md:hidden animate-slide-up">
      <div className="glass-card p-4 rounded-xl border border-moss/30 shadow-lg">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-moss/20 flex items-center justify-center shrink-0">
            <Download className="w-5 h-5 text-moss" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white">Install Janus</p>
            <p className="text-xs text-white/60 mt-0.5">
              Add to home screen for faster access
            </p>
          </div>
          <button
            onClick={dismiss}
            className="p-1 hover:bg-white/10 rounded-lg transition-colors shrink-0"
            aria-label="Close"
          >
            <X className="w-4 h-4 text-white/40" />
          </button>
        </div>
        <div className="flex gap-2 mt-3">
          <button
            onClick={dismiss}
            className="flex-1 px-4 py-2 text-sm text-white/70 hover:text-white transition-colors"
          >
            Later
          </button>
          <button
            onClick={install}
            className="flex-1 px-4 py-2 bg-moss text-black text-sm font-medium rounded-lg hover:bg-moss/90 transition-colors"
          >
            Install
          </button>
        </div>
      </div>
    </div>
  );
}
```

### FR-6: Share Target Handler Page

```typescript
// ui/src/app/chat/share/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

type ShareMode = 'chat' | 'read-to-me' | null;

export default function ShareTargetPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<ShareMode>(null);
  const [content, setContent] = useState<{ title?: string; text?: string; url?: string } | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    // Extract shared content from URL params (GET) or form data (POST)
    const title = searchParams.get('title') || undefined;
    const text = searchParams.get('text') || undefined;
    const url = searchParams.get('url') || undefined;

    if (title || text || url) {
      setContent({ title, text, url });
    }
  }, [searchParams]);

  const handleChat = () => {
    // Combine content into a message
    let message = '';
    if (content?.title) message += content.title + '\n\n';
    if (content?.text) message += content.text + '\n\n';
    if (content?.url) message += content.url;

    // Redirect to chat with the content as initial message
    const params = new URLSearchParams({
      initial: message.trim(),
      source: 'share'
    });
    router.push(`/chat?${params.toString()}`);
  };

  const handleReadToMe = async () => {
    setIsProcessing(true);
    setMode('read-to-me');

    // Combine content
    let textToRead = '';
    if (content?.text) {
      textToRead = content.text;
    }

    // If URL, we need to extract content via the agent
    if (content?.url && !content?.text) {
      // Redirect to chat with special read-to-me instruction
      const instruction = `Please visit this URL, extract the main content, create a transcript suitable for reading aloud, and then read it to me: ${content.url}`;
      const params = new URLSearchParams({
        initial: instruction,
        autoSubmit: 'true',
        tts: 'true',
        source: 'share'
      });
      router.push(`/chat?${params.toString()}`);
      return;
    }

    // If just text, go directly to TTS
    if (textToRead) {
      const params = new URLSearchParams({
        initial: `Read the following text to me:\n\n${textToRead}`,
        autoSubmit: 'true',
        tts: 'true',
        source: 'share'
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

        {/* Content preview */}
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

        {/* Action buttons */}
        <div className="space-y-3">
          <button
            onClick={handleChat}
            className="w-full p-4 bg-moss/20 hover:bg-moss/30 border border-moss/30 rounded-xl text-left transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-moss/30 flex items-center justify-center">
                <svg className="w-5 h-5 text-moss" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
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
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
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
```

### FR-7: Chat Page Share Handling

```typescript
// ui/src/app/chat/page.tsx - Add to existing page

// Handle URL parameters for share target
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const initial = params.get('initial');
  const autoSubmit = params.get('autoSubmit') === 'true';
  const enableTTS = params.get('tts') === 'true';

  if (initial) {
    // Set initial message in textarea
    setInput(initial);

    // Enable TTS for response if requested
    if (enableTTS) {
      setAutoPlayTTS(true);
    }

    // Auto-submit if requested
    if (autoSubmit) {
      setTimeout(() => {
        handleSubmit(new Event('submit') as any);
      }, 500);
    }

    // Clean URL
    window.history.replaceState({}, '', '/chat');
  }
}, []);
```

### FR-8: Next.js Configuration

```typescript
// ui/next.config.js - Add headers for SW

const nextConfig = {
  // ... existing config

  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
        ],
      },
      {
        source: '/manifest.json',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
        ],
      },
    ];
  },
};
```

### FR-9: Manifest Link in Layout

```typescript
// ui/src/app/layout.tsx - Add to <head>

<link rel="manifest" href="/manifest.json" />
<meta name="theme-color" content="#63D297" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<meta name="apple-mobile-web-app-title" content="Janus" />
<link rel="apple-touch-icon" href="/icons/icon-192.png" />
```

### FR-10: PWA Toast in Chat Layout

```typescript
// ui/src/app/chat/layout.tsx

import { PWAInstallToast } from '@/components/PWAInstallToast';

export default function ChatLayout({ children }) {
  return (
    <>
      {children}
      <PWAInstallToast />
    </>
  );
}
```

## Technical Notes

### Auto-Update Strategy

1. **Service Worker**: Uses `skipWaiting()` and `clients.claim()` for immediate activation
2. **Network-First**: Always load from network, cache only as fallback
3. **Periodic Checks**: Check for updates every 5 minutes
4. **Visibility Check**: Check for updates when app comes to foreground
5. **No-Cache Headers**: SW and manifest are never cached

### Share Target Registration

Android and supported browsers automatically register the app as a Share Target when:
- The PWA is installed
- `share_target` is defined in the manifest
- The app runs over HTTPS

The two options (Chat/Read-to-me) are implemented via the Share Target Page since the manifest only supports one share target endpoint.

### iOS Limitations

- iOS does not natively support Share Target
- PWA install must be done manually via "Add to Home Screen"
- `beforeinstallprompt` event not available on iOS

### Dismiss Timing Logic

- **First dismiss**: Show again after 2 days minimum
- **Subsequent dismisses**: Show again after 7 days minimum
- **Storage**: `localStorage` with timestamp and dismiss count
- **Never show**: If already running as PWA (`display-mode: standalone`)

## Acceptance Criteria

- [ ] PWA manifest correctly configured
- [ ] Service worker registers and auto-updates
- [ ] Install toast appears only on mobile
- [ ] Install toast does not appear when already PWA
- [ ] Dismiss timing works (2 days, then weekly)
- [ ] Update banner appears when new version available
- [ ] Share Target works on Android
- [ ] "Use in Chat" correctly inserts text
- [ ] "Read to Me" starts TTS
- [ ] URL content is extracted and read aloud
- [ ] App starts in /chat area

## Files to Create/Modify

```
ui/
├── public/
│   ├── manifest.json
│   ├── sw.js
│   └── icons/
│       ├── icon-192.png
│       ├── icon-512.png
│       ├── chat-icon.png
│       └── speaker-icon.png
├── src/
│   ├── hooks/
│   │   ├── usePWAInstall.ts
│   │   └── usePWAUpdate.ts
│   ├── components/
│   │   └── PWAInstallToast.tsx
│   └── app/
│       ├── layout.tsx (modify - add manifest link)
│       └── chat/
│           ├── layout.tsx (modify - add PWA toast)
│           ├── page.tsx (modify - handle share params)
│           └── share/
│               └── page.tsx (new)
└── next.config.js (modify - add headers)
```

## Related Specs

- `specs/47_text_to_speech_response_playback.md` - TTS implementation
- `specs/11_chat_ui.md` - Chat UI base
- `specs/82_chat_ui_polish.md` - UI polish

NR_OF_TRIES: 0
