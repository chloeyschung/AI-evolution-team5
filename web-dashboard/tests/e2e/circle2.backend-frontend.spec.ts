import { expect, test } from '@playwright/test';

test.describe('Circle 2: Backend-to-Frontend', () => {
  test('OAuth callback sends real backend request and frontend remains stable', async ({ page }) => {
    const requestPromise = page.waitForRequest(
      (request) => request.url().includes('/api/v1/auth/google/code') && request.method() === 'POST',
    );

    await page.goto('/oauth-callback?code=circle2_test_code');

    const oauthRequest = await requestPromise;
    expect(oauthRequest.url()).toContain('/api/v1/auth/google/code');

    await expect(page.getByTestId('oauth-callback-page')).toBeVisible();
    await expect(page).toHaveURL(/\/oauth-callback|\/login/);
  });
});
