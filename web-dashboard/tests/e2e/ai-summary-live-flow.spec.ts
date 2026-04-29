import { expect, test } from '@playwright/test';

const BACKEND_BASE_URL = process.env.E2E_BACKEND_BASE_URL ?? 'http://127.0.0.1:8000';
const TEST_EMAIL = process.env.E2E_EMAIL ?? 'testtest@test.com';
const TEST_PASSWORD = process.env.E2E_PASSWORD ?? '3644@3644';

const RSS_FEEDS = [
  'https://feeds.bbci.co.uk/news/rss.xml',
  'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
  'https://feeds.npr.org/1001/rss.xml',
];

const FALLBACK_URLS = [
  'https://www.bbc.co.uk/news',
  'https://www.npr.org/sections/news/',
];

function extractCandidateLinks(xml: string): string[] {
  const matches = [...xml.matchAll(/<link>(https?:\/\/[^<]+)<\/link>/g)];
  return matches
    .map((match) => match[1])
    .filter((url) => !url.includes('/rss') && !url.includes('feeds.') && url.includes('news'));
}

async function fetchRandomNewsUrl(): Promise<string> {
  const shuffled = [...RSS_FEEDS].sort(() => Math.random() - 0.5);

  for (const feedUrl of shuffled) {
    try {
      const response = await fetch(feedUrl);
      if (!response.ok) continue;
      const xml = await response.text();
      const links = extractCandidateLinks(xml);
      if (links.length > 0) {
        return links[Math.floor(Math.random() * links.length)];
      }
    } catch {
      // Ignore feed-level failures and try next source.
    }
  }

  return FALLBACK_URLS[Math.floor(Math.random() * FALLBACK_URLS.length)];
}

test.describe('Live AI Summary E2E', () => {
  test('logs in, shares a real random news URL, and renders generated summary on dashboard', async ({ page, request }) => {
    test.setTimeout(180_000);

    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_EMAIL);
    await page.fill('input[name="password"]', TEST_PASSWORD);
    await page.getByRole('button', { name: /sign in with email/i }).click();
    await page.waitForURL(/\/dashboard/, { timeout: 20_000 });

    const accessToken = await page.evaluate(() => localStorage.getItem('briefly_access_token'));
    expect(accessToken).toBeTruthy();

    const randomNewsUrl = await fetchRandomNewsUrl();
    const shareResponse = await request.post(`${BACKEND_BASE_URL}/api/v1/share`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      data: {
        content: randomNewsUrl,
        platform: 'e2e_playwright',
      },
    });

    expect(shareResponse.status(), await shareResponse.text()).toBe(201);
    const shared = await shareResponse.json() as {
      id: number;
      summary: string | null;
      url: string;
    };

    expect(shared.id).toBeGreaterThan(0);
    expect(shared.url).toContain('http');
    expect((shared.summary ?? '').trim().length).toBeGreaterThan(30);

    await page.goto('/dashboard');
    const card = page.getByTestId(`content-card-${shared.id}`);
    await expect(card).toBeVisible({ timeout: 20_000 });

    const normalizedSummarySnippet = (shared.summary ?? '')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 40);
    await expect(card).toContainText(normalizedSummarySnippet);
    await expect(card).not.toContainText('No summary yet');
  });
});
