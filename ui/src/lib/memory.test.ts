import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { isMemoryEnabled, setMemoryEnabled } from './memory';

describe('memory', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('defaults to enabled when unset', () => {
    expect(isMemoryEnabled()).toBe(true);
  });

  it('persists memory toggle state', () => {
    setMemoryEnabled(false);
    expect(isMemoryEnabled()).toBe(false);

    setMemoryEnabled(true);
    expect(isMemoryEnabled()).toBe(true);
  });

  it('falls back to default when storage errors', () => {
    vi.spyOn(window.localStorage, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });

    expect(isMemoryEnabled()).toBe(true);
  });

  it('does not throw when storage rejects writes', () => {
    vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });

    expect(() => setMemoryEnabled(true)).not.toThrow();
  });
});
