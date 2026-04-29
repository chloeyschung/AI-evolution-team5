import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const seedPath = path.resolve(__dirname, '.circle3-seed.json');

test.describe('Circle 3: DB-to-Backend-to-Frontend', () => {
  test.beforeAll(() => {
    execSync(`bash -lc 'cd .. && set -a && source .env && set +a && uv run python web-dashboard/tests/e2e/scripts/seed_fullstack.py web-dashboard/tests/e2e/.circle3-seed.json'`, {
      stdio: 'inherit',
    });
  });

  test('seeded database content flows through backend into frontend rendering', async ({ page, request }) => {
    const seed = JSON.parse(readFileSync(seedPath, 'utf-8')) as {
      access_token: string;
      refresh_token: string;
      user_id: number;
      email: string;
    };

    const backendResponse = await request.get('http://127.0.0.1:8000/api/v1/content?limit=20', {
      headers: {
        Authorization: `Bearer ${seed.access_token}`,
      },
    });

    expect(backendResponse.status()).toBe(200);
    const backendItems = (await backendResponse.json()) as Array<{ id: number; title: string }>;
    expect(backendItems.some((item) => item.title === 'Circle 3: DB to Backend to Frontend')).toBeTruthy();

    await page.addInitScript((data) => {
      localStorage.setItem(
        'briefly_auth_state',
        JSON.stringify({
          isAuthenticated: true,
          user: {
            id: data.user_id,
            email: data.email,
            display_name: data.email,
          },
        }),
      );
    }, seed);

    await page.route('**/api/v1/content**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(backendItems),
      });
    });

    await page.route('**/api/v1/platforms', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ platform: 'web', count: backendItems.length }]),
      });
    });

    await page.goto('/dashboard');
    await expect(page.getByText('Circle 3: DB to Backend to Frontend')).toBeVisible();
  });
});
