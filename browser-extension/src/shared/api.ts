import { ShareData, ShareResponse, PageMetadata, RecentContentItem } from './types';
import { authManager } from './auth';
import { storageManager } from './storage';
import { resolveApiBaseUrl } from './runtime-config';
import { parseApiErrorResponse } from './api-errors';

export class APIError extends Error {
  constructor(
    public message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class APIClient {
  private readonly TIMEOUT_MS = 60000; // 60 second timeout — LLM summarization can take 10-30 s

  private readonly errorMessages: Record<number, string> = {
    401: 'Session expired. Please login again.',
    403: 'Access denied. Please check your permissions.',
    429: 'Too many requests. Please wait a moment and try again.',
    500: 'Server error. Please try again later.',
  };

  async shareContent(metadata: PageMetadata, selectedText?: string): Promise<ShareResponse> {
    let token: string;
    try {
      token = await authManager.getAccessToken();
    } catch {
      throw new APIError('Authentication required. Please login again.', 401, 'AUTH_REQUIRED');
    }

    const settings = await storageManager.getSettings();
    const apiBaseUrl = resolveApiBaseUrl(settings.apiBaseUrl);

    const shareData: ShareData = {
      content: selectedText || metadata.url,
      platform: this.detectPlatform(metadata.url),
      metadata: {
        url: metadata.url,
        title: metadata.title,
        author: metadata.author,
        description: metadata.description,
        content_type: metadata.type,
      },
      options: {
        auto_summarize: settings.autoSummarize,
      },
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.TIMEOUT_MS);

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/share`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(shareData),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.status === 401) {
        await storageManager.clearTokens();
        throw new APIError(this.errorMessages[401], 401, 'SESSION_EXPIRED');
      }

      if (!response.ok) {
        const fallback = this.errorMessages[response.status] || `Request failed with status ${response.status}`;
        const parsed = await parseApiErrorResponse(response, fallback);
        throw new APIError(parsed.message, response.status, parsed.code);
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new APIError('Request timeout. Please check your connection and try again.', 0, 'TIMEOUT');
      }

      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new APIError('Network error. Please check your internet connection.', 0, 'NETWORK_ERROR');
      }

      throw error;
    }
  }

  async getRecentContent(limit = 5): Promise<RecentContentItem[]> {
    let token: string;
    try {
      token = await authManager.getAccessToken();
    } catch {
      throw new APIError('Authentication required. Please login again.', 401, 'AUTH_REQUIRED');
    }

    const settings = await storageManager.getSettings();
    const apiBaseUrl = resolveApiBaseUrl(settings.apiBaseUrl);

    const response = await fetch(`${apiBaseUrl}/api/v1/content?limit=${Math.max(1, Math.min(limit, 10))}&offset=0`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 401) {
      await storageManager.clearTokens();
      throw new APIError(this.errorMessages[401], 401, 'SESSION_EXPIRED');
    }

    if (!response.ok) {
      const fallback = this.errorMessages[response.status] || `Request failed with status ${response.status}`;
      const parsed = await parseApiErrorResponse(response, fallback);
      throw new APIError(parsed.message, response.status, parsed.code);
    }

    const data = await response.json() as { items?: Array<Record<string, unknown>> };
    const items = Array.isArray(data.items) ? data.items : [];
    return items.map((item) => ({
      id: Number(item.id),
      title: typeof item.title === 'string' ? item.title : null,
      url: typeof item.url === 'string' ? item.url : '',
      platform: typeof item.platform === 'string' ? item.platform : 'web',
      created_at: typeof item.created_at === 'string' ? item.created_at : '',
    }));
  }

  private detectPlatform(url: string): string {
    let domain: string;
    try {
      domain = new URL(url).hostname.replace('www.', '');
    } catch {
      return 'web';
    }

    const platformMap: Record<string, string> = {
      'youtube.com': 'youtube',
      'youtu.be': 'youtube',
      'linkedin.com': 'linkedin',
      'twitter.com': 'twitter',
      'x.com': 'twitter',
      'medium.com': 'medium',
      'instagram.com': 'instagram',
      'facebook.com': 'facebook',
      'tiktok.com': 'tiktok',
      'reddit.com': 'reddit',
    };

    return platformMap[domain] || 'web';
  }
}

export const apiClient = new APIClient();
