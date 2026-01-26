export const PRE_RELEASE_HEADER = 'X-PreReleasePassword';
export const PRE_RELEASE_STORAGE_KEY = 'janusPreReleasePassword';

export function getStoredPreReleasePassword(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return window.localStorage.getItem(PRE_RELEASE_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storePreReleasePassword(password: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(PRE_RELEASE_STORAGE_KEY, password);
  } catch {
    // Ignore storage failures.
  }
}

export function clearPreReleasePassword(): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.removeItem(PRE_RELEASE_STORAGE_KEY);
  } catch {
    // Ignore storage failures.
  }
}

export function applyPreReleaseHeader(headersInit?: HeadersInit): Headers {
  const headers = new Headers(headersInit || {});
  const password = getStoredPreReleasePassword();
  if (password) {
    headers.set(PRE_RELEASE_HEADER, password);
  }
  return headers;
}
