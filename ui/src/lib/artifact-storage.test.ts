import { describe, it, expect } from 'vitest';

import { sanitizeSegment, safeJoin, resolveExtension, mimeTypeFromExtension } from './artifact-storage';

describe('artifact-storage', () => {
  describe('sanitizeSegment', () => {
    it('preserves safe characters', () => {
      expect(sanitizeSegment('file-name_123.txt')).toBe('file-name_123.txt');
    });

    it('replaces unsafe characters with underscores', () => {
      expect(sanitizeSegment('../etc/passwd')).toBe('.._etc_passwd');
    });

    it('truncates long segments', () => {
      const long = 'a'.repeat(200);
      expect(sanitizeSegment(long).length).toBe(160);
    });

    it('returns fallback for empty input', () => {
      expect(sanitizeSegment('')).toBe('artifact');
    });
  });

  describe('safeJoin', () => {
    it('resolves valid paths within root', () => {
      const result = safeJoin('/artifacts', 'chat123', 'file.png');
      expect(result).toBe('/artifacts/chat123/file.png');
    });

    it('throws on path traversal attempts', () => {
      expect(() => safeJoin('/artifacts', '..', 'etc', 'passwd')).toThrow('Invalid artifact path');
    });

    it('throws on absolute path escape', () => {
      expect(() => safeJoin('/artifacts', '/etc/passwd')).toThrow('Invalid artifact path');
    });
  });

  describe('resolveExtension', () => {
    it('extracts extension from display name', () => {
      expect(resolveExtension('report.pdf')).toBe('.pdf');
    });

    it('falls back to mime type mapping', () => {
      expect(resolveExtension(undefined, 'image/png')).toBe('.png');
    });

    it('returns .bin for unknown types', () => {
      expect(resolveExtension(undefined, 'application/x-custom')).toBe('.bin');
    });
  });

  describe('mimeTypeFromExtension', () => {
    it('maps known extensions', () => {
      expect(mimeTypeFromExtension('.png')).toBe('image/png');
      expect(mimeTypeFromExtension('.jpg')).toBe('image/jpg');
    });

    it('returns undefined for unknown extensions', () => {
      expect(mimeTypeFromExtension('.xyz')).toBeUndefined();
    });
  });
});
