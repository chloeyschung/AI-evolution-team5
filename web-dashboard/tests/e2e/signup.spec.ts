import { test, expect } from '@playwright/test';

/**
 * E2E tests for signup flow.
 *
 * These tests verify:
 * - Signup page is accessible and renders correctly
 * - Form submission creates account via /api/v1/auth/register endpoint
 * - No double-prefix path issue (/api/api/v1/... should NOT occur)
 * - Success state displays verification message
 */

test.describe('Signup Flow', () => {
  test('should display signup page with all form fields', async ({ page }) => {
    await page.goto('/signup');

    // Should be on signup page
    await expect(page).toHaveURL(/\/signup/);

    // Should have all required form fields
    await expect(page.getByPlaceholder('Email')).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Password', exact: true })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Confirm password' })).toBeVisible();
    await expect(page.getByRole('button', { name: /create account/i })).toBeVisible();
  });

  test('should submit signup form and create account', async ({ page }) => {
    // Track API requests to verify correct endpoint
    const apiRequests: { url: string; method: string }[] = [];
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiRequests.push({
          url: request.url(),
          method: request.method(),
        });
      }
    });

    await page.goto('/signup');

    // Fill form with test data
    const testEmail = `playwright-test-${Date.now()}@example.com`;
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[name="password"]', 'password123');
    await page.fill('input[name="confirm"]', 'password123');

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for API response
    await page.waitForTimeout(3000);

    // Verify correct API endpoint was called (no double prefix)
    const registerRequest = apiRequests.find(
      r => r.method === 'POST' && r.url.includes('/register')
    );
    expect(registerRequest).toBeDefined();
    expect(registerRequest!.url).toBe('http://localhost:3001/api/v1/auth/register');

    // Verify no double-prefix path occurred
    const doublePrefixRequests = apiRequests.filter(r =>
      r.url.includes('/api/api/')
    );
    expect(doublePrefixRequests).toHaveLength(0);

    // Should show success message
    await expect(page.getByRole('heading', { name: /check your inbox/i })).toBeVisible();
  });

  test('should show error when passwords do not match', async ({ page }) => {
    await page.goto('/signup');

    // Fill form with mismatched passwords
    await page.fill('input[type="email"]', 'mismatch@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.fill('input[name="confirm"]', 'password456');

    // Submit form
    await page.click('button[type="submit"]');

    // Should show password mismatch error
    await expect(page.getByText(/passwords do not match/i)).toBeVisible();
  });

  test('should handle existing email error', async ({ page }) => {
    // Track API responses
    let registerResponseStatus: number | null = null;
    page.on('response', async response => {
      if (response.url().includes('/register')) {
        registerResponseStatus = response.status();
      }
    });

    await page.goto('/signup');

    // Use a known email (if exists in test database) or just verify the flow
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.fill('input[name="confirm"]', 'password123');

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for response
    await page.waitForTimeout(3000);

    // Should have made the API call (status could be 201, 409, etc.)
    expect(registerResponseStatus).not.toBeNull();
  });

  test('should have correct API path without double prefix', async ({ page }) => {
    // This test specifically verifies the fix for the double-prefix bug
    // where VITE_API_BASE_URL=/api caused /api/api/v1/... paths

    const apiV1Requests: string[] = [];
    page.on('request', request => {
      const url = request.url();
      // Only track actual API v1 requests (not Vite dev server requests to /src/api/)
      if (url.includes('/api/v1/')) {
        apiV1Requests.push(url);
      }
    });

    await page.goto('/signup');

    // Fill and submit form
    const testEmail = `path-test-${Date.now()}@example.com`;
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[name="password"]', 'password123');
    await page.fill('input[name="confirm"]', 'password123');

    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // Should have made at least one API v1 request
    expect(apiV1Requests.length).toBeGreaterThan(0);

    // All API v1 requests should NOT have double /api/api/ prefix
    for (const url of apiV1Requests) {
      expect(url).not.toContain('/api/api/');
    }
  });
});
