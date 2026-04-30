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

  test('should submit signup form through the canonical API path', async ({ page }) => {
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
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Registration successful. Please check your email to verify your account.',
        }),
      });
    });

    await page.goto('/signup');

    // Fill form with test data
    const testEmail = `playwright-test-${Date.now()}@example.com`;
    await page.fill('input[type="email"]', testEmail);
    await page.fill('input[name="password"]', 'password123');
    await page.fill('input[name="confirm"]', 'password123');

    const registerResponsePromise = page.waitForResponse(
      response => response.request().method() === 'POST' && response.url().includes('/api/v1/auth/register')
    );
    await page.click('button[type="submit"]');
    await registerResponsePromise;

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

});
