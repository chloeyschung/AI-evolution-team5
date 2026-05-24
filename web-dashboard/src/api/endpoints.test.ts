import { beforeEach, describe, expect, test, vi } from 'vitest';
import { getContent, getPendingContent, searchContent } from './endpoints';
import type { Content } from '../types';

const { mockClient } = vi.hoisted(() => ({
  mockClient: {
    get: vi.fn(),
  },
}));

vi.mock('./client', () => ({
  getApiClient: () => mockClient,
}));

const contentItem = {
  id: 1001,
  platform: 'web',
  content_type: 'article',
  url: 'https://example.com/article',
  title: 'Wrapped content item',
  author: 'Briefly Test',
  summary: 'Backend paginated responses should be unwrapped by endpoint helpers.',
  status: 'inbox',
  created_at: '2026-04-30T00:00:00Z',
  updated_at: '2026-04-30T00:00:00Z',
} as Content;

describe('content endpoint helpers', () => {
  beforeEach(() => {
    mockClient.get.mockReset();
  });

  test('unwraps paginated content responses for dashboard lists', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: { items: [contentItem], has_more: true },
    });

    const result = await getContent(
      { status: 'all', platform: null, dateFrom: null, dateTo: null, category: null },
      { option: 'recency', order: 'desc' },
      2,
      20
    );

    expect(mockClient.get).toHaveBeenCalledWith('/api/v1/content', {
      params: { limit: 20, offset: 20, sort: 'recency', order: 'desc' },
    });
    expect(result).toEqual({ items: [contentItem], hasMore: true });
  });

  test('unwraps pending content responses for inbox cards', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: { items: [contentItem], has_more: false },
    });

    const result = await getPendingContent(10, 'web');

    expect(mockClient.get).toHaveBeenCalledWith('/api/v1/content/pending', {
      params: { limit: 10, platform: 'web' },
    });
    expect(result).toEqual([contentItem]);
  });

  test('unwraps search responses for client-side consumers', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: { items: [contentItem], has_more: false },
    });

    const result = await searchContent('wrapped', 5, 0);

    expect(mockClient.get).toHaveBeenCalledWith('/api/v1/search', {
      params: { q: 'wrapped', limit: 5, offset: 0 },
    });
    expect(result).toEqual([contentItem]);
  });
});
