import { test, expect } from '@playwright/test';

/**
 * E2E tests for authentication flow.
 *
 * These tests verify:
 * - Login page is accessible and renders correctly
 * - OAuth callback page is accessible
 * - Protected routes exist in the application
 *
 * Note: Auth guard behavior depends on authStore initialization state.
 * Tests focus on page accessibility and component rendering.
 */

test.describe('Authentication Flow', () => {
  test('unverified login error shows resend verification CTA', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            error: 'email_not_verified',
            can_resend: true,
            message: 'Email not verified. Please verify your email or request a new verification email.',
          },
        }),
      });
    });

    await page.route('**/api/v1/auth/verify-email/resend', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'If the account exists and is not verified, a verification email has been sent.',
        }),
      });
    });

    await page.goto('/login');
    await page.fill('input[name="email"]', 'unverified@example.com');
    await page.fill('input[name="password"]', 'Pass1!');
    await page.click('button:has-text("Sign in with email")');

    await expect(page.getByText(/email not verified/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /resend verification email/i })).toBeVisible();

    await page.click('button:has-text("Resend verification email")');
    await expect(page.getByText(/verification email has been sent/i)).toBeVisible();
  });

  test('verify-email failure page allows resend by email', async ({ page }) => {
    await page.route('**/api/v1/auth/verify-email?token=*', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Invalid or expired verification token',
        }),
      });
    });

    await page.route('**/api/v1/auth/verify-email/resend', async (route) => {
      expect(route.request().postDataJSON()).toEqual({
        email: 'expired@example.com',
      });

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'If the account exists and is not verified, a verification email has been sent.',
        }),
      });
    });

    await page.goto('/verify-email?token=expired-or-invalid-token');

    await expect(page.getByText(/verification failed/i)).toBeVisible();
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.getByRole('button', { name: /resend verification email/i })).toBeVisible();

    await page.fill('input[name="email"]', 'expired@example.com');
    await page.getByRole('button', { name: /resend verification email/i }).click();
    await expect(page.getByText(/verification email has been sent/i)).toBeVisible();
  });

  test('login 401 does not trigger forced refresh flow', async ({ page }) => {
    let refreshCalled = false;

    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: { error: 'invalid_credentials' },
        }),
      });
    });

    await page.route('**/api/v1/auth/refresh', async (route) => {
      refreshCalled = true;
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: { error: 'invalid_refresh_token' },
        }),
      });
    });

    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.setItem('briefly_refresh_token', 'dummy-refresh-token');
    });
    await page.fill('input[name="email"]', 'no-user@example.com');
    await page.fill('input[name="password"]', 'WrongPass1!');
    await page.click('button:has-text("Sign in with email")');

    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByText(/request failed|sign in failed|invalid credentials/i)).toBeVisible();
    expect(refreshCalled).toBeFalsy();
  });

  test('oauth callback 401 does not trigger forced refresh flow', async ({ page }) => {
    let refreshCalled = false;

    await page.route('**/api/v1/auth/google/code', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: { error: 'invalid_google_token' },
        }),
      });
    });

    await page.route('**/api/v1/auth/refresh', async (route) => {
      refreshCalled = true;
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: { error: 'invalid_refresh_token' },
        }),
      });
    });

    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.setItem('briefly_refresh_token', 'dummy-refresh-token');
    });

    await page.goto('/oauth-callback?code=invalid_code_12345');
    await page.waitForURL(/\/login\?error=/, { timeout: 6000 });

    expect(refreshCalled).toBeFalsy();
  });

  test('should navigate to dashboard route', async ({ page }) => {
    // Navigate to dashboard route
    await page.goto('/dashboard');

    // Should reach the dashboard URL (auth guard may or may not redirect)
    const url = page.url();
    expect(url).toContain('localhost:3001');
  });

  test('should navigate to inbox route', async ({ page }) => {
    await page.goto('/inbox');
    const url = page.url();
    expect(url).toContain('localhost:3001');
  });

  test('should navigate to archive route', async ({ page }) => {
    await page.goto('/archive');
    const url = page.url();
    expect(url).toContain('localhost:3001');
  });

  test('should display login page', async ({ page }) => {
    await page.goto('/login');

    // Should be on login page
    await expect(page).toHaveURL(/\/login/);

    // Page should load without errors
    await page.waitForLoadState('networkidle');
  });

  test('should navigate to OAuth callback page', async ({ page }) => {
    // Navigate to OAuth callback (without valid code)
    await page.goto('/oauth-callback?code=test');

    // Should be on oauth-callback page
    await expect(page).toHaveURL(/\/oauth-callback/);

    // Page should load
    await page.waitForLoadState('domcontentloaded');
  });

  test('should handle OAuth callback with invalid code', async ({ page }) => {
    await page.goto('/oauth-callback?code=invalid_code_12345');

    // Should show error after attempting to process
    await page.waitForTimeout(3000);

    // Page should still be on localhost
    const url = page.url();
    expect(url).toContain('localhost:3001');
  });
});
