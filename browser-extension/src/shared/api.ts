import { ShareData, ShareResponse, PageMetadata } from './types';
import { authManager } from './auth';
import { storageManager } from './storage';

export class APIClient {
  async shareContent(metadata: PageMetadata, selectedText?: string): Promise<ShareResponse> {
    const token = await authManager.getAccessToken();
    const settings = await storageManager.getSettings();

    const shareData: ShareData = {
      content: selectedText || metadata.url,
      platform: this.detectPlatform(metadata.url),
      metadata: {
        title: metadata.title,
        author: metadata.author,
        description: metadata.description,
        content_type: metadata.type,
      },
    };

    const response = await fetch(`${settings.apiBaseUrl}/api/v1/share`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(shareData),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Failed to share content');
    }

    return response.json();
  }

  private detectPlatform(url: string): string {
    const domain = new URL(url).hostname.replace('www.', '');

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
