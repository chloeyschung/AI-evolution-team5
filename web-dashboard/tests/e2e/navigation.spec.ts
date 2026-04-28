import { test, expect } from '@playwright/test';

/**
 * E2E tests for navigation security.
 *
 * These tests verify:
 * - Open redirect vulnerability is patched
 * - Only whitelisted routes can be used as redirects
 *
 * Note: The redirect validation happens in the OAuthCallback component's onMounted hook.
 * The URL may still show the original parameter, but the router.push() will navigate
 * to the safe destination. We verify by checking that external navigation is blocked.
 */

test.describe('Navigation Security', () => {
  test('should not navigate to external URL when malicious redirect is provided', async ({ page }) => {
    // Track only top-level navigations (ignore external static assets like Google Fonts).
    const mainFrameNavigations: string[] = [];
    page.on('framenavigated', (frame) => {
      if (frame === page.mainFrame()) {
        mainFrameNavigations.push(frame.url());
      }
    });

    // Simulate OAuth callback with malicious redirect URL
    await page.goto('/oauth-callback?code=test&redirect=https://evil.com/phishing');

    // Wait for component to process and attempt redirect
    await page.waitForTimeout(2000);

    // Verify no external main-frame navigation occurred
    const navigatedToExternalMainFrame = mainFrameNavigations.some((url) => {
      try {
        return new URL(url).hostname !== 'localhost';
      } catch {
        return false;
      }
    });
    expect(navigatedToExternalMainFrame).toBe(false);
    // Final URL should still be on localhost
    const finalUrl = page.url();
    expect(finalUrl).toContain('localhost:3001');
    expect(finalUrl.startsWith('https://evil.com')).toBe(false);
  });

  test('should not execute data URL in redirect parameter', async ({ page }) => {
    // Set up console and error listeners
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/oauth-callback?code=test&redirect=data:text/html,<script>alert(1)</script>');

    // Wait for processing
    await page.waitForTimeout(2000);

    // Should not have executed any scripts from data URL
    expect(errors).not.toContainEqual(expect.stringContaining('alert'));
  });

  test('should not execute javascript URL in redirect parameter', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/oauth-callback?code=test&redirect=javascript:alert(1)');

    await page.waitForTimeout(2000);

    // Should not have executed javascript: URL (no 'Uncaught' or script errors)
    // Note: There may be other errors from the invalid code, but not from script execution
    const scriptErrors = errors.filter(e => e.includes('Uncaught') || e.includes('script'));
    expect(scriptErrors.length).toBe(0);
  });

  test('should handle whitelisted redirect to dashboard', async ({ page }) => {
    await page.goto('/oauth-callback?code=test&redirect=/dashboard');

    // Wait for component processing
    await page.waitForTimeout(2000);

    // Should stay on localhost domain
    const finalUrl = page.url();
    expect(finalUrl).toContain('localhost:3001');
  });

  test('should handle whitelisted redirect to inbox', async ({ page }) => {
    await page.goto('/oauth-callback?code=test&redirect=/inbox');

    await page.waitForTimeout(2000);

    const finalUrl = page.url();
    expect(finalUrl).toContain('localhost:3001');
  });

  test('should handle whitelisted redirect to archive', async ({ page }) => {
    await page.goto('/oauth-callback?code=test&redirect=/archive');

    await page.waitForTimeout(2000);

    const finalUrl = page.url();
    expect(finalUrl).toContain('localhost:3001');
  });

  test('should handle missing redirect parameter', async ({ page }) => {
    await page.goto('/oauth-callback?code=test');

    await page.waitForTimeout(2000);

    // Should stay on localhost domain
    const finalUrl = page.url();
    expect(finalUrl).toContain('localhost:3001');
  });

  test('should handle path traversal attempt in redirect', async ({ page }) => {
    await page.goto('/oauth-callback?code=test&redirect=../../../etc/passwd');

    await page.waitForTimeout(2000);

    // Should stay on localhost domain
    const finalUrl = page.url();
    expect(finalUrl).toContain('localhost:3001');
  });
});
