import { expect, test } from '@playwright/test';

test.describe('Circle 1: Frontend-to-Frontend', () => {
  test('renders bite-sized inbox cards with mocked API and supports swipe actions', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem(
        'briefly_auth_state',
        JSON.stringify({
          isAuthenticated: true,
          user: { id: 1, email: 'circle1@briefly.local', display_name: 'Circle 1' },
        }),
      );
    });

    await page.route('**/api/v1/auth/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ is_authenticated: true, user_id: 1, email: 'circle1@briefly.local' }),
      });
    });

    await page.route('**/api/v1/content/pending**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 1001,
            platform: 'youtube',
            content_type: 'video',
            url: 'https://example.com/one',
            title: 'Circle 1 Mock Card',
            author: 'Frontend Test',
            summary: 'This card proves frontend rendering with deterministic API stubs.',
            status: 'inbox',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.route('**/api/v1/platforms', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ platform: 'youtube', count: 1 }]),
      });
    });

    await page.route('**/api/v1/swipe', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 1, content_id: 1001, action: 'keep' }),
      });
    });

    await page.goto('/inbox');

    await expect(page.getByTestId('inbox-page')).toBeVisible();
    await expect(page.getByText('Circle 1 Mock Card')).toBeVisible();

    await page.getByRole('button', { name: 'Keep' }).click();

    await expect(page.getByText('Circle 1 Mock Card')).toBeVisible();
  });
});
