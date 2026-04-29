import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const TEST_EMAIL = process.env.E2E_EMAIL ?? 'testtest@test.com';
const TEST_PASSWORD = process.env.E2E_PASSWORD ?? '3644@3644';

type DiagnosticRecord = {
  route: string;
  consoleErrors: string[];
  requestFailures: string[];
  httpFailures: string[];
  screenshot: string;
};

test.describe('Dashboard Dynamic Diagnostics', () => {
  test('collects live console/network evidence across all menu routes', async ({ page }) => {
    test.setTimeout(240_000);

    const outDir = path.join(process.cwd(), 'test-results', 'dynamic-diagnostics');
    mkdirSync(outDir, { recursive: true });

    const allConsoleErrors: string[] = [];
    const allRequestFailures: string[] = [];
    const allHttpFailures: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        allConsoleErrors.push(`[console:${msg.type()}] ${msg.text()}`);
      }
    });

    page.on('requestfailed', (req) => {
      allRequestFailures.push(`[requestfailed] ${req.method()} ${req.url()} :: ${req.failure()?.errorText ?? 'unknown'}`);
    });

    page.on('response', async (res) => {
      if (res.status() >= 400) {
        allHttpFailures.push(`[http${res.status()}] ${res.request().method()} ${res.url()}`);
      }
    });

    // Step 1: Login (live backend)
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_EMAIL);
    await page.fill('input[name="password"]', TEST_PASSWORD);
    await page.getByRole('button', { name: /sign in with email/i }).click();
    await page.waitForURL(/\/dashboard/, { timeout: 25_000 });
    await expect(page.getByTestId('dashboard-page')).toBeVisible();

    // Keep per-route snapshots.
    const diagnostics: DiagnosticRecord[] = [];
    const routes: Array<{ route: string; testId: string }> = [
      { route: '/dashboard', testId: 'dashboard-page' },
      { route: '/inbox', testId: 'inbox-page' },
      { route: '/archive', testId: 'archive-page' },
      { route: '/analytics', testId: 'analytics-page' },
      { route: '/settings', testId: 'settings-page' },
    ];

    let consumedConsole = 0;
    let consumedRequestFail = 0;
    let consumedHttpFail = 0;

    for (const item of routes) {
      await page.goto(item.route);
      await expect(page.getByTestId(item.testId)).toBeVisible({ timeout: 20_000 });
      await page.waitForTimeout(1200);

      const shotPath = path.join(outDir, `${item.route.replace('/', '') || 'root'}.png`);
      await page.screenshot({ path: shotPath, fullPage: true });

      // Capture only newly observed issues for this route.
      const newConsole = allConsoleErrors.slice(consumedConsole);
      const newReqFail = allRequestFailures.slice(consumedRequestFail);
      const newHttpFail = allHttpFailures.slice(consumedHttpFail);
      consumedConsole = allConsoleErrors.length;
      consumedRequestFail = allRequestFailures.length;
      consumedHttpFail = allHttpFailures.length;

      diagnostics.push({
        route: item.route,
        consoleErrors: newConsole,
        requestFailures: newReqFail,
        httpFailures: newHttpFail,
        screenshot: shotPath,
      });
    }

    // Settings behavior sanity: save feedback should be understandable.
    await page.goto('/settings');
    await page.selectOption('#theme', 'light');
    await page.getByRole('button', { name: /save settings/i }).click();
    await expect(page.getByText(/saved\. your workspace is updated\./i)).toBeVisible();

    const reportPath = path.join(outDir, 'diagnostics.json');
    writeFileSync(reportPath, JSON.stringify(diagnostics, null, 2), 'utf-8');

    console.log('\n[DYNAMIC-DIAGNOSTICS] report:', reportPath);
    for (const rec of diagnostics) {
      console.log(`[DYNAMIC-DIAGNOSTICS] ${rec.route}`);
      console.log(`  screenshot=${rec.screenshot}`);
      console.log(`  consoleErrors=${rec.consoleErrors.length}`);
      console.log(`  requestFailures=${rec.requestFailures.length}`);
      console.log(`  httpFailures=${rec.httpFailures.length}`);
      for (const c of rec.consoleErrors) console.log(`    ${c}`);
      for (const r of rec.requestFailures) console.log(`    ${r}`);
      for (const h of rec.httpFailures) console.log(`    ${h}`);
    }

    // Hard failure gate for critical client-side failures.
    // (Keep 4xx in httpFailures as evidence, but only fail on console/request transport errors.)
    expect(allConsoleErrors, 'Console errors should be empty').toEqual([]);
    expect(allRequestFailures, 'Network transport failures should be empty').toEqual([]);
  });
});
