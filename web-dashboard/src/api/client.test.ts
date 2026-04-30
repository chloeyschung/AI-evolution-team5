import { describe, expect, test } from 'vitest';
import { normalizeApiBaseUrl } from './client';

describe('normalizeApiBaseUrl', () => {
  test('removes a trailing /api prefix because endpoint helpers already include /api/v1', () => {
    expect(normalizeApiBaseUrl('/api')).toBe('');
    expect(normalizeApiBaseUrl('https://api.example.com/api')).toBe('https://api.example.com');
  });

  test('keeps backend origins that do not include the API path prefix', () => {
    expect(normalizeApiBaseUrl('http://127.0.0.1:8000')).toBe('http://127.0.0.1:8000');
    expect(normalizeApiBaseUrl('')).toBe('');
  });
});
