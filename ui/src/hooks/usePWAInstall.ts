import { useCallback, useEffect, useState } from 'react';

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
};

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
      return JSON.parse(stored) as PromptState;
    }
  } catch {
    // ignore storage errors
  }
  return { dismissed: false, dismissedAt: null, dismissCount: 0 };
}

function savePromptState(state: PromptState) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function shouldShowPrompt(): boolean {
  const state = getPromptState();

  if (!state.dismissed || !state.dismissedAt) {
    return true;
  }

  const now = Date.now();
  const daysSinceDismiss = (now - state.dismissedAt) / (1000 * 60 * 60 * 24);

  if (state.dismissCount === 1) {
    return daysSinceDismiss >= 2;
  }

  return daysSinceDismiss >= 7;
}

export function usePWAInstall() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [canInstall, setCanInstall] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);

  const isPWA = useCallback(() => {
    if (typeof window === 'undefined') return false;

    if (window.matchMedia('(display-mode: standalone)').matches) return true;

    if ((window.navigator as { standalone?: boolean }).standalone === true) return true;

    if (new URLSearchParams(window.location.search).get('source') === 'pwa') return true;

    return false;
  }, []);

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

    if (!isMobile()) return;

    if (isPWA()) {
      // Schedule state update outside effect render cycle
      queueMicrotask(() => {
        setIsInstalled(true);
      });
      return;
    }

    const handler = (event: Event) => {
      event.preventDefault();
      const promptEvent = event as BeforeInstallPromptEvent;
      setDeferredPrompt(promptEvent);
      setCanInstall(true);

      if (shouldShowPrompt()) {
        setShowPrompt(true);
      }
    };

    const installedHandler = () => {
      setIsInstalled(true);
      setCanInstall(false);
      setShowPrompt(false);
    };

    window.addEventListener('beforeinstallprompt', handler);
    window.addEventListener('appinstalled', installedHandler);

    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
      window.removeEventListener('appinstalled', installedHandler);
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
