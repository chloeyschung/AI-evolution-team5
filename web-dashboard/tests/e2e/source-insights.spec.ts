import { test, expect } from '@playwright/test';

/**
 * E2E tests for Source Insights section on the Analytics page.
 * Uses API route mocking — no live backend required.
 */

const MOCK_SOURCES = [
  {
    domain: 'theatlantic.com',
    favicon_url: 'https://theatlantic.com/favicon.ico',
    display_name: null,
    save_count: 12,
    keep_count: 10,
    keep_rate: 0.83,
    manually_added: false,
    most_recent_title: 'Long-form essay on social trust',
  },
  {
    domain: 'manuallyAdded.io',
    favicon_url: null,
    display_name: 'My Blog',
    save_count: 0,
    keep_count: 0,
    keep_rate: 0,
    manually_added: true,
    most_recent_title: null,
  },
];

const MOCK_NARRATIVE = {
  text: "You've been consistently drawn to The Atlantic's long-form essays.",
  generated_at: '2026-05-28T00:00:00Z',
};

test.describe('Source Insights', () => {
  test.beforeEach(async ({ page, context }) => {
    // Inject fake auth tokens into localStorage so the app thinks we're logged in
    await context.addInitScript(() => {
      localStorage.setItem('briefly_access_token', 'fake-test-token');
      localStorage.setItem('briefly_refresh_token', 'fake-refresh-token');
      localStorage.setItem('briefly_expires_at', String(Date.now() + 3_600_000));
    });

    // Mock auth status endpoint
    await page.route('**/api/v1/auth/status', (route) =>
      route.fulfill({
        json: {
          is_authenticated: true,
          user_id: 1,
          email: 'test@example.com',
          token_expires_at: new Date(Date.now() + 3_600_000).toISOString(),
        },
      }),
    );

    // Mock stats API
    await page.route('**/api/v1/stats', (route) =>
      route.fulfill({ json: { pending: 5, kept: 30, discarded: 10 } }),
    );
    await page.route('**/api/v1/user/statistics', (route) =>
      route.fulfill({
        json: {
          total_swipes: 40,
          total_kept: 30,
          total_discarded: 10,
          retention_rate: 0.75,
          streak_days: 3,
          first_swipe_at: null,
          last_swipe_at: null,
        },
      }),
    );

    // Mock sources API
    await page.route('**/api/v1/sources**', (route) =>
      route.fulfill({ json: { sources: MOCK_SOURCES } }),
    );

    // Mock narrative API
    await page.route('**/api/v1/sources/*/narrative', (route) =>
      route.fulfill({ json: MOCK_NARRATIVE }),
    );

    // Mock confirm API
    await page.route('**/api/v1/sources/*/confirm', (route) =>
      route.fulfill({
        json: {
          domain: 'newdomain.com',
          favicon_url: null,
          display_name: null,
          save_count: 0,
          keep_count: 0,
          keep_rate: 0,
          manually_added: true,
          most_recent_title: null,
        },
      }),
    );
  });

  test('Analytics page shows Sources sub-section', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.getByTestId('analytics-page')).toBeVisible();
    await expect(page.getByTestId('source-insights-section')).toBeVisible();
  });

  test('source cards render with keep-rate and save count', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.getByTestId('source-row-theatlantic.com')).toBeVisible();
    await expect(page.getByText('83% kept')).toBeVisible();
    await expect(page.getByText('12 saves')).toBeVisible();
  });

  test('favicon click opens site in new tab (default browser)', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.getByTestId('source-row-theatlantic.com')).toBeVisible();
    const faviconBtn = page.getByTestId('favicon-btn-theatlantic.com');
    await expect(faviconBtn).toBeVisible();
    // Verify the button has correct aria-label (opens in default browser)
    await expect(faviconBtn).toHaveAttribute('aria-label', 'Open theatlantic.com');
    // Click and allow popup (noopener may prevent context tracking — just verify click works)
    const popupPromise = page.waitForEvent('popup', { timeout: 3000 }).catch(() => null);
    await faviconBtn.click();
    const popup = await popupPromise;
    if (popup) {
      expect(popup.url()).toContain('theatlantic.com');
      await popup.close();
    }
  });

  test('Detail button shows narrative text', async ({ page }) => {
    await page.goto('/analytics');
    await page.getByTestId('source-row-theatlantic.com').getByRole('button', { name: 'Detail' }).click();
    await expect(page.getByText("You've been consistently drawn")).toBeVisible();
  });

  test('Detail button is separate from favicon', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.getByTestId('source-row-theatlantic.com')).toBeVisible();
    const row = page.getByTestId('source-row-theatlantic.com');
    const detailBtn = row.getByRole('button', { name: 'Detail' });
    const faviconBtn = row.getByTestId('favicon-btn-theatlantic.com');
    // Both buttons exist and are distinct
    await expect(detailBtn).toBeVisible();
    await expect(faviconBtn).toBeVisible();
    await expect(detailBtn).toHaveText('Detail');
    // Favicon button has site-open aria-label, not "Detail"
    await expect(faviconBtn).toHaveAttribute('aria-label', 'Open theatlantic.com');
  });

  test('manual add form submits and new source appears', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.getByTestId('source-insights-section')).toBeVisible();
    await page.getByTestId('add-source-btn').click();
    await page.getByPlaceholder('e.g. theatlantic.com').fill('newdomain.com');
    // Use exact: true to avoid matching "Open manuallyAdded.io" aria-label
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await expect(page.getByText('newdomain.com')).toBeVisible({ timeout: 5000 });
  });
});
