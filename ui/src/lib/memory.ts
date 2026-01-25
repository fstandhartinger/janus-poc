const MEMORY_ENABLED_KEY = 'janus_memory_enabled';
const DEFAULT_MEMORY_ENABLED = true;

export function isMemoryEnabled(): boolean {
  if (typeof window === 'undefined') {
    return DEFAULT_MEMORY_ENABLED;
  }

  try {
    const stored = window.localStorage.getItem(MEMORY_ENABLED_KEY);
    if (stored === null) {
      return DEFAULT_MEMORY_ENABLED;
    }
    return stored !== 'false';
  } catch {
    return DEFAULT_MEMORY_ENABLED;
  }
}

export function setMemoryEnabled(enabled: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(MEMORY_ENABLED_KEY, enabled ? 'true' : 'false');
  } catch {
    // Swallow storage errors (private mode / SSR).
  }
}
