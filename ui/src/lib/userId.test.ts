import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearUserId, getLocalUserId, getUserId } from './userId';

describe('userId', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('crypto', {
      randomUUID: vi.fn(() => '550e8400-e29b-41d4-a716-446655440000'),
    } as unknown as Crypto);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('prefers the authenticated user id when provided', () => {
    const first = getUserId({ userId: 'chutes-user-123' });
    expect(first).toBe('chutes-user-123');
  });

  it('generates and persists a local user id', () => {
    const first = getLocalUserId();
    const second = getLocalUserId();

    expect(first).toBe('550e8400-e29b-41d4-a716-446655440000');
    expect(second).toBe('550e8400-e29b-41d4-a716-446655440000');
    expect(localStorage.getItem('janus_user_id')).toBe('550e8400-e29b-41d4-a716-446655440000');

    clearUserId();
    expect(localStorage.getItem('janus_user_id')).toBeNull();
  });

  it('returns empty string when storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });

    expect(getLocalUserId()).toBe('');
  });
});
