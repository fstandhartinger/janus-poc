import { useCallback, useEffect, useState } from 'react';

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
      state.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  }, [state.registration]);

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    let registration: ServiceWorkerRegistration | null = null;
    let updateFoundHandler: (() => void) | null = null;
    let visibilityHandler: (() => void) | null = null;
    let controllerHandler: (() => void) | null = null;
    let intervalId: number | null = null;

    const registerSW = async () => {
      try {
        registration = await navigator.serviceWorker.register('/sw.js', {
          updateViaCache: 'none',
        });

        const handleUpdateFound = () => {
          const newWorker = registration?.installing;
          if (!newWorker) return;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              setState({ updateAvailable: true, registration });
            }
          });
        };

        updateFoundHandler = handleUpdateFound;
        registration.addEventListener('updatefound', handleUpdateFound);

        if (registration.waiting) {
          setState({ updateAvailable: true, registration });
        } else {
          setState({ updateAvailable: false, registration });
        }

        intervalId = window.setInterval(() => {
          registration?.update();
        }, 5 * 60 * 1000);

        visibilityHandler = () => {
          if (document.visibilityState === 'visible') {
            registration?.update();
          }
        };
        document.addEventListener('visibilitychange', visibilityHandler);

        controllerHandler = () => {
          window.location.reload();
        };
        navigator.serviceWorker.addEventListener('controllerchange', controllerHandler);
      } catch (error) {
        console.error('[PWA] Service worker registration failed:', error);
      }
    };

    registerSW();

    return () => {
      if (intervalId) {
        window.clearInterval(intervalId);
      }
      if (registration && updateFoundHandler) {
        registration.removeEventListener('updatefound', updateFoundHandler);
      }
      if (visibilityHandler) {
        document.removeEventListener('visibilitychange', visibilityHandler);
      }
      if (controllerHandler) {
        navigator.serviceWorker.removeEventListener('controllerchange', controllerHandler);
      }
    };
  }, []);

  return {
    updateAvailable: state.updateAvailable,
    applyUpdate,
  };
}
