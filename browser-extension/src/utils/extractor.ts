import { PageMetadata, ContentType } from '../shared/types';

export class PageExtractor {
  async extractMetadata(): Promise<PageMetadata> {
    const url = window.location.href;
    const title = this.extractTitle();
    const author = this.extractAuthor();
    const description = this.extractDescription();
    const type = this.detectContentType(url);

    return { url, title, author, description, type };
  }

  private extractTitle(): string | null {
    // Try og:title first (Open Graph)
    const ogTitle = document.querySelector('meta[property="og:title"]')?.content;
    if (ogTitle) return ogTitle;

    // Try twitter:title
    const twitterTitle = document.querySelector('meta[name="twitter:title"]')?.content;
    if (twitterTitle) return twitterTitle;

    // Try standard title tag
    const titleTag = document.querySelector('title')?.textContent;
    if (titleTag) return titleTag.trim();

    // Try h1 as fallback
    const h1 = document.querySelector('h1')?.textContent;
    if (h1) return h1.trim();

    return null;
  }

  private extractAuthor(): string | null {
    // Try og:author
    const ogAuthor = document.querySelector('meta[property="og:author"]')?.content;
    if (ogAuthor) return ogAuthor;

    // Try article:author
    const articleAuthor = document.querySelector('meta[property="article:author"]')?.content;
    if (articleAuthor) return articleAuthor;

    // Try twitter:creator
    const twitterCreator = document.querySelector('meta[name="twitter:creator"]')?.content;
    if (twitterCreator) return twitterCreator.replace('@', '');

    // Try standard author meta
    const authorMeta = document.querySelector('meta[name="author"]')?.content;
    if (authorMeta) return authorMeta;

    // Try article author
    const articleAuthorTag = document.querySelector('meta[name="article:author"]')?.content;
    if (articleAuthorTag) return articleAuthorTag;

    return null;
  }

  private extractDescription(): string | null {
    // Try og:description first
    const ogDesc = document.querySelector('meta[property="og:description"]')?.content;
    if (ogDesc) return ogDesc;

    // Try twitter:description
    const twitterDesc = document.querySelector('meta[name="twitter:description"]')?.content;
    if (twitterDesc) return twitterDesc;

    // Try standard description
    const descMeta = document.querySelector('meta[name="description"]')?.content;
    if (descMeta) return descMeta;

    // Try content
    const contentMeta = document.querySelector('meta[name="content"]')?.content;
    if (contentMeta) return contentMeta;

    return null;
  }

  private detectContentType(url: string): ContentType {
    const urlLower = url.toLowerCase();
    const domain = new URL(url).hostname;

    // Video platforms
    if (domain.includes('youtube') || domain.includes('youtu.be') ||
        domain.includes('vimeo') || domain.includes('twitch')) {
      return 'video';
    }

    // Social platforms
    if (domain.includes('twitter') || domain.includes('x.com') ||
        domain.includes('facebook') || domain.includes('instagram') ||
        domain.includes('linkedin') || domain.includes('tiktok') ||
        domain.includes('reddit') || domain.includes('medium')) {
      return 'social';
    }

    // Image platforms
    if (domain.includes('imgur') || domain.includes('flickr') ||
        domain.includes('unsplash') || domain.includes('pinterest')) {
      return 'image';
    }

    // Check for article indicators
    if (this.hasArticleIndicators()) {
      return 'article';
    }

    return 'unknown';
  }

  private hasArticleIndicators(): boolean {
    // Check for article-specific meta tags
    const articleMeta = document.querySelector('meta[property="article:"]');
    if (articleMeta) return true;

    // Check for news-specific tags
    const newsMeta = document.querySelector('meta[name="news"]');
    if (newsMeta) return true;

    // Check for long-form content structure
    const articleTag = document.querySelector('article');
    if (articleTag) {
      const textContent = articleTag.textContent || '';
      if (textContent.length > 500) return true;
    }

    return false;
  }

  getSelectedText(): string | null {
    const selection = window.getSelection();
    if (selection && selection.toString().trim()) {
      return selection.toString().trim();
    }
    return null;
  }
}

export const pageExtractor = new PageExtractor();
