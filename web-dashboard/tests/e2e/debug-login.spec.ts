import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';

/**
 * Debug test to observe the email login flow behavior.
 *
 * This test will:
 * 1. Intercept the login API call to see the request/response
 * 2. Observe localStorage after login
 * 3. Observe URL navigation
 *
 * Run with: npx playwright test tests/e2e/debug-login.spec.ts
 *
 * Prerequisites:
 * - Create a test user first: uv run scripts/create_test_user.py <context>
 */

test('debug email login flow - observe token storage and navigation', async ({ page }) => {
  // Track API requests and responses
  const apiCalls: { method: string; url: string; status?: number; response?: any }[] = [];

  page.on('request', request => {
    if (request.url().includes('/api/')) {
      console.log(`>>> ${request.method()} ${request.url()}`);
    }
  });

  page.on('response', async response => {
    if (response.url().includes('/api/')) {
      const status = response.status();
      let body = null;
      try {
        body = await response.json();
      } catch {}
      apiCalls.push({
        method: response.request().method(),
        url: response.url(),
        status,
        response: body
      });
      console.log(`<<< ${status} ${response.url()}`);
      if (body) console.log('    Response:', JSON.stringify(body).substring(0, 200));
    }
  });

  // Enable console logging
  page.on('console', msg => console.log(`[PAGE] ${msg.type()}: ${msg.text()}`));

  // Navigate to login page
  console.log('\n=== NAVIGATING TO /login ===\n');
  await page.goto('/login');
  await expect(page).toHaveURL(/.*login/);

  // Fill in email and password - get the most recently created test user
  // Test users are created by: uv run scripts/create_test_user.py <context>
  // The test auto-discovers the latest test user via --get-latest flag
  let testEmail: string;
  try {
    // Use absolute path to avoid working directory issues
    const scriptPath = '/media/younghwan/3006F86D14CC96B4/project/Briefly/scripts/create_test_user.py';
    const emailResult = execSync(`cd /media/younghwan/3006F86D14CC96B4/project/Briefly && uv run python scripts/create_test_user.py --get-latest`, {
      encoding: 'utf-8',
    }).trim();
    testEmail = emailResult;
  } catch (e) {
    console.error('Failed to get test user from database:', e);
    throw new Error('No test user found. Run: uv run scripts/create_test_user.py <context>');
  }
  const testPassword = 'testtest'; // Fixed password used by create_test_user.py

  console.log(`\n=== FILLING FORM with ${testEmail} ===\n`);
  await page.fill('input[name="email"]', testEmail);
  await page.fill('input[name="password"]', testPassword);

  // Submit the form
  console.log('\n=== CLICKING LOGIN BUTTON ===\n');
  const loginButton = page.getByRole('button', { name: /sign in/i });
  await loginButton.click();

  // Wait for API response or timeout
  console.log('\n=== WAITING FOR RESPONSE (up to 5s) ===\n');
  await page.waitForTimeout(5000);

  // Check localStorage
  console.log('\n=== STORAGE STATE ===');
  const storageState = await page.context().storageState();
  const tokens = storageState.origins?.[0]?.localStorage || [];
  const accessToken = tokens.find(i => i.name === 'briefly_access_token');
  const refreshToken = tokens.find(i => i.name === 'briefly_refresh_token');
  console.log('briefly_access_token:', accessToken?.value ? 'EXISTS (' + accessToken.value.substring(0, 20) + '...)' : 'MISSING');
  console.log('briefly_refresh_token:', refreshToken?.value ? 'EXISTS (' + refreshToken.value.substring(0, 20) + '...)' : 'MISSING');

  // Check current URL
  const currentUrl = page.url();
  console.log('\n=== NAVIGATION STATE ===');
  console.log('Current URL:', currentUrl);
  console.log('Still on /login?', currentUrl.endsWith('/login'));

  // Summary
  console.log('\n=== SUMMARY ===');
  console.log('Login API called:', apiCalls.some(c => c.url.includes('/auth/login') && c.method === 'POST'));
  console.log('Login API 200 OK:', apiCalls.some(c => c.url.includes('/auth/login') && c.status === 200));
  console.log('Tokens stored:', !!(accessToken?.value && refreshToken?.value));
  console.log('Navigated away from /login:', !currentUrl.endsWith('/login'));
});
