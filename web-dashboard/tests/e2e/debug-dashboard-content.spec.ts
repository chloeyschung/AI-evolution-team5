import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

/**
 * Debug test to observe the content API response shape and store state.
 *
 * This test will:
 * 1. Login with test user
 * 2. Intercept the /api/v1/content call to see the response shape
 * 3. Observe the store state after loadContent()
 * 4. Verify if items is an array or object
 *
 * Run with: npx playwright test tests/e2e/debug-dashboard-content.spec.ts
 */

test('debug content API response shape and store state', async ({ page }) => {
  // Track API responses
  const contentApiResponses: any[] = [];

  page.on('response', async response => {
    if (response.url().includes('/api/v1/content') && !response.url().includes('/pending')) {
      const status = response.status();
      let body = null;
      try {
        body = await response.json();
      } catch {}
      contentApiResponses.push({
        url: response.url(),
        status,
        body
      });
      console.log(`\n<<< ${status} ${response.url()}`);
      console.log('    Response shape:', JSON.stringify(body, null, 2).substring(0, 500));
    }
  });

  // Enable console logging
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('contentStore') || text.includes('items type')) {
      console.log(`[PAGE] ${msg.type()}: ${text}`);
    }
  });

  // Get test user
  let testEmail: string;
  try {
    const emailResult = execSync(
      'cd /media/younghwan/3006F86D14CC96B4/project/Briefly && uv run python scripts/create_test_user.py --get-latest',
      { encoding: 'utf-8' }
    ).trim();
    testEmail = emailResult;
  } catch (e) {
    console.error('Failed to get test user from database:', e);
    throw new Error('No test user found. Run: uv run scripts/create_test_user.py <context>');
  }
  const testPassword = 'testtest';

  console.log(`\n=== TEST USER: ${testEmail} ===\n`);

  // Navigate to login and login
  console.log('\n=== NAVIGATING TO /login ===\n');
  await page.goto('/login');
  await expect(page).toHaveURL(/.*login/);

  console.log('\n=== FILLING LOGIN FORM ===\n');
  await page.fill('input[name="email"]', testEmail);
  await page.fill('input[name="password"]', testPassword);

  console.log('\n=== CLICKING LOGIN ===\n');
  const loginButton = page.getByRole('button', { name: /sign in/i });
  await loginButton.click();

  // Wait for navigation to dashboard
  console.log('\n=== WAITING FOR /dashboard ===\n');
  await page.waitForURL(/.*dashboard/, { timeout: 10000 });
  console.log('Navigated to dashboard');

  // Wait for content API call
  console.log('\n=== WAITING FOR CONTENT API CALL ===\n');
  await page.waitForTimeout(2000);

  // Check API response
  console.log('\n=== API RESPONSE ANALYSIS ===\n');
  const contentResponse = contentApiResponses.find(r => r.url.includes('/api/v1/content') && !r.url.includes('/pending'));

  if (contentResponse) {
    console.log('Response status:', contentResponse.status);
    console.log('Response body type:', typeof contentResponse.body);
    console.log('Has "items" key?', 'items' in contentResponse.body);

    if (contentResponse.body && 'items' in contentResponse.body) {
      console.log('contentResponse.body.items type:', Array.isArray(contentResponse.body.items) ? 'ARRAY' : typeof contentResponse.body.items);
      console.log('contentResponse.body.items length:', contentResponse.body.items?.length);
      console.log('Has "has_more" key?', 'has_more' in contentResponse.body);
    }
  } else {
    console.log('No /api/v1/content response found!');
  }

  // Check for errors on page
  console.log('\n=== CHECKING FOR RENDER ERRORS ===\n');
  const hasMapError = await page.evaluate(() => {
    return typeof (window as any).__mapError === 'boolean' ? (window as any).__mapError : false;
  });

  // Summary
  console.log('\n=== SUMMARY ===\n');
  if (contentResponse?.body) {
    console.log('API returns wrapper object {"items": [...]}:', 'items' in contentResponse.body);
    console.log('API items is array:', Array.isArray(contentResponse.body.items));
  }
  console.log('Bug confirmed (API returns wrapper, not array):', contentResponse?.body && 'items' in contentResponse.body);
});
