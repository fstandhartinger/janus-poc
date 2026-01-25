const USER_ID_STORAGE_KEY = 'janus_user_id';

export type AuthUserRef = { userId?: string | null } | null | undefined;

const generateFallbackId = () =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16);
    const value = char === 'x' ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });

export function getUserId(session?: AuthUserRef): string {
  if (session?.userId) {
    return session.userId;
  }

  return getLocalUserId();
}

export function getLocalUserId(): string {
  if (typeof window === 'undefined') {
    return '';
  }

  try {
    let userId = window.localStorage.getItem(USER_ID_STORAGE_KEY);
    if (!userId) {
      if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
        userId = crypto.randomUUID();
      } else {
        userId = generateFallbackId();
      }
      window.localStorage.setItem(USER_ID_STORAGE_KEY, userId);
    }
    return userId;
  } catch {
    return '';
  }
}

export function clearUserId(): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.removeItem(USER_ID_STORAGE_KEY);
  } catch {
    // Swallow storage errors (private mode / SSR).
  }
}
