import { test, expect } from '@playwright/test';

/**
 * Debug test to trace the exact value flow of contentStore.items.
 * Tests each hypothesis serially.
 */

test('trace contentStore.items - H1: API response shape', async ({ page }) => {
  // Track API responses
  let apiResponse: any = null;

  page.on('response', async response => {
    if (response.url().includes('/api/v1/content?limit=') && !response.url().includes('/pending')) {
      try {
        apiResponse = await response.json();
      } catch {}
    }
  });

  // Login flow - use hardcoded test user from previous creation
  await page.goto('/login');
  await page.fill('input[name="email"]', 'debug-infinite-loading-signing-in-during-login-20260419-01@test.com');
  await page.fill('input[name="password"]', 'testtest');
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(/.*dashboard/, { timeout: 10000 });
  await page.waitForTimeout(1000);

  console.log('\n=== H1 TEST: API Response Shape ===\n');
  console.log('API response:', JSON.stringify(apiResponse, null, 2));
  console.log('Type of apiResponse:', typeof apiResponse);
  console.log('Type of apiResponse.items:', typeof apiResponse?.items);
  console.log('Array.isArray(apiResponse.items):', Array.isArray(apiResponse?.items));

  // H1 hypothesis: If apiResponse is {items: [...], has_more: ...} then the API is correct
  // The bug must be in how endpoints.ts processes this response
  expect(apiResponse).toHaveProperty('items');
  expect(Array.isArray(apiResponse?.items)).toBe(true);
  console.log('H1 RESULT: API returns correct shape {items: [...]} ✓');
  console.log('→ Bug is NOT in API, must be in endpoints.ts processing\n');
});

test('trace contentStore.items - H2/H3: Store loadContent processing', async ({ page }) => {
  // Intercept the getContent call and log what the store receives
  await page.goto('/login');
  await page.fill('input[name="email"]', 'debug-infinite-loading-signing-in-during-login-20260419-01@test.com');
  await page.fill('input[name="password"]', 'testtest');
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(/.*dashboard/, { timeout: 10000 });

  // Inject code to monitor the store
  await page.evaluate(() => {
    // Store the original console.error to capture the error
    window.__capturedErrors: string[] = [];
    const originalError = console.error;
    console.error = (...args) => {
      if (args.some(a => typeof a === 'string' && a.includes('map is not a function'))) {
        (window as any).__capturedErrors = (window as any).__capturedErrors || [];
        (window as any).__capturedErrors.push(args.join(' '));
      }
      originalError(...args);
    };
  });

  await page.waitForTimeout(1000);

  console.log('\n=== H2/H3 TEST: Store Processing ===\n');

  // Check if error was captured
  const errors = await page.evaluate(() => (window as any).__capturedErrors || []);
  console.log('Captured errors:', errors);

  // Now let's check what the endpoints.ts file is doing
  // We can't directly inspect it, but we can check the network response
  // and compare with what the store should receive

  console.log('H2/H3 RESULT: Need to check endpoints.ts code directly\n');
});
