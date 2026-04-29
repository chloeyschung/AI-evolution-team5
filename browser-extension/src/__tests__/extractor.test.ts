import { describe, it, expect, beforeEach, vi } from 'vitest';
import { PageExtractor } from '../utils/extractor';

// Mock DOM environment
const mockDocument = {
  querySelector: vi.fn(),
  body: {
    appendChild: vi.fn(),
  },
};

const mockWindow = {
  location: {
    href: 'https://example.com/article',
  },
  getSelection: vi.fn(),
  addEventListener: vi.fn(),
};

// Setup mock DOM before tests
beforeEach(() => {
  vi.clearAllMocks();
  (global as any).document = mockDocument;
  (global as any).window = mockWindow;
});

describe('PageExtractor', () => {
  let extractor: PageExtractor;

  beforeEach(() => {
    extractor = new PageExtractor();
  });

  describe('extractMetadata', () => {
    it('should extract metadata from Open Graph tags', async () => {
      const mockMeta = { content: 'Test Article Title' };
      mockDocument.querySelector = vi.fn().mockReturnValue(mockMeta as any);
      mockWindow.location.href = 'https://medium.com/article/123';

      const metadata = await extractor['extractMetadata']();

      expect(metadata.url).toBe('https://medium.com/article/123');
      expect(metadata.title).toBe('Test Article Title');
      expect(metadata.type).toBe('social');
    });

    it('should fallback to title tag when og:title not available', async () => {
      mockDocument.querySelector = vi.fn().mockImplementation((selector: string) => {
        if (selector === 'meta[property="og:title"]') return null;
        if (selector === 'meta[name="twitter:title"]') return null;
        if (selector === 'title') return { textContent: 'Fallback Title' };
        return null;
      });

      const metadata = await extractor['extractMetadata']();

      expect(metadata.title).toBe('Fallback Title');
    });

    it('should detect video content type for YouTube URLs', async () => {
      mockDocument.querySelector = vi.fn().mockReturnValue(null);
      mockWindow.location.href = 'https://youtube.com/watch?v=123';

      const metadata = await extractor['extractMetadata']();

      expect(metadata.type).toBe('video');
    });

    it('should detect social content type for Twitter URLs', async () => {
      mockDocument.querySelector = vi.fn().mockReturnValue(null);
      mockWindow.location.href = 'https://twitter.com/user/status/123';

      const metadata = await extractor['extractMetadata']();

      expect(metadata.type).toBe('social');
    });
  });

  describe('getSelectedText', () => {
    it('should return selected text when available', () => {
      const mockSelection = {
        toString: () => 'Selected text content',
      };
      mockWindow.getSelection = vi.fn().mockReturnValue(mockSelection);

      const selectedText = extractor.getSelectedText();

      expect(selectedText).toBe('Selected text content');
    });

    it('should return null when no text is selected', () => {
      const mockSelection = {
        toString: () => '',
      };
      mockWindow.getSelection = vi.fn().mockReturnValue(mockSelection);

      const selectedText = extractor.getSelectedText();

      expect(selectedText).toBeNull();
    });
  });
});
