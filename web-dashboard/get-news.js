import { chromium } from 'playwright';
import { randomInt } from 'crypto';

/**
 * Fetch current news headlines using Playwright
 *
 * Human-like patterns to avoid bot detection:
 * - Random delays between actions
 * - Realistic user agents
 * - Mouse movements
 * - Multiple source fallbacks
 *
 * Usage: node get-news.js
 */

const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
];

const randomDelay = (min, max) => new Promise(resolve => setTimeout(resolve, randomInt(min, max)));

const getRandomUserAgent = () => USER_AGENTS[randomInt(0, USER_AGENTS.length)];

const newsSources = [
  {
    name: 'Hacker News',
    url: 'https://news.ycombinator.com',
    selectors: ['.titleline > a[href^="http"]'],
    maxResults: 10,
  },
  {
    name: 'BBC News',
    url: 'https://www.bbc.com/news',
    selectors: [
      'h3 a[href^="https://www.bbc.com"]',
      'article h2 a',
      'div[data-testid="article-link"] h2',
    ],
    maxResults: 10,
  },
  {
    name: 'Reuters',
    url: 'https://www.reuters.com/news/world-news',
    selectors: [
      'h3 a[href^="https://www.reuters.com"]',
      'article h2 a',
      '.story-title a',
    ],
    maxResults: 10,
  },
  {
    name: 'AP News',
    url: 'https://apnews.com/',
    selectors: [
      'h2 a[href^="https://apnews.com"]',
      'article h1 a',
      '.headline a',
    ],
    maxResults: 10,
  },
  {
    name: 'TechCrunch',
    url: 'https://techcrunch.com/',
    selectors: [
      'h2 a[href^="https://techcrunch.com"]',
      'h3 a[href^="https://techcrunch.com"]',
      '.post-title a',
    ],
    maxResults: 10,
  },
  {
    name: 'The Verge',
    url: 'https://www.theverge.com/',
    selectors: [
      'h2 a[href^="https://www.theverge.com"]',
      'h3 a[href^="https://www.theverge.com"]',
      '.postTitle a',
    ],
    maxResults: 10,
  },
];

async function fetchFromSource(source, page) {
  console.log(`\n  Trying ${source.name}...`);

  try {
    await page.goto(source.url, {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    // Human-like: random delay after page load
    await randomDelay(1500, 3500);

    // Human-like: random mouse movement
    await page.mouse.move(randomInt(100, 800), randomInt(100, 400));
    await randomDelay(200, 800);

    // Try each selector
    for (const selector of source.selectors) {
      const elements = await page.locator(selector).all();

      if (elements.length > 0) {
        const titles = [];

        for (let i = 0; i < Math.min(source.maxResults, elements.length); i++) {
          try {
            const text = await elements[i].textContent();
            const clean = text?.trim();
            if (clean && clean.length > 5 && clean.length < 200) {
              titles.push(clean);
            }
          } catch (e) {
            // Skip this element
          }
        }

        if (titles.length >= 3) {
          return titles;
        }
      }

      // Small delay between selector attempts
      await randomDelay(300, 800);
    }
  } catch (err) {
    console.log(`    Failed: ${err.message.slice(0, 50)}`);
  }

  return null;
}

async function fetchNews() {
  console.log('\n╔════════════════════════════════════════════════════════╗');
  console.log('║         Fetching Current News Headlines                ║');
  console.log('╚════════════════════════════════════════════════════════╝\n');

  // Set random user agent
  const userAgent = getRandomUserAgent();
  console.log(`User Agent: ${userAgent.slice(0, 60)}...\n`);

  const browser = await chromium.launch({
    headless: true,
  });

  const context = await browser.newContext({
    userAgent: userAgent,
    viewport: { width: 1920, height: 1080 },
  });

  const page = await context.newPage();

  // Initial delay
  await randomDelay(1000, 2000);

  for (const source of newsSources) {
    const titles = await fetchFromSource(source, page);

    if (titles && titles.length >= 3) {
      console.log(`\n✅ Successfully fetched from ${source.name}!\n`);
      console.log('Top Stories:\n');

      titles.forEach((title, i) => {
        console.log(`  ${i + 1}. ${title}`);
      });

      console.log(`\n📰 Source: ${source.name} (${source.url})`);
      console.log(`📊 Total: ${titles.length} stories\n`);

      await browser.close();
      return titles;
    }

    // Delay between sources
    await randomDelay(1000, 2500);
  }

  await browser.close();
  console.log('\n❌ Failed to fetch news from all sources. Try again later.\n');
  return null;
}

// Run
fetchNews().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
