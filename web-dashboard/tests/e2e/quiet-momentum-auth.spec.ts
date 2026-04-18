import { expect, test } from '@playwright/test';

async function expectStackedForm(page: import('@playwright/test').Page, controls: string[]) {
  const form = page.locator('form');
  await expect(form).toHaveCSS('display', 'grid');
  await expect(form).toHaveCSS('row-gap', '12px');

  for (const selector of controls) {
    await expect(page.locator(selector)).toBeVisible();
  }

  const actualOrder = await form.evaluate((node) => {
    return Array.from(node.children).map((child) => {
      const element = child as HTMLInputElement | HTMLButtonElement;
      return element.getAttribute('name') || element.getAttribute('type') || element.tagName.toLowerCase();
    });
  });

  expect(actualOrder).toEqual(
    controls.map((selector) => {
      if (selector.includes('name="email"')) return 'email';
      if (selector.includes('name="password"')) return 'password';
      if (selector.includes('name="confirm"')) return 'confirm';
      if (selector.includes('type="submit"')) return 'submit';
      return selector;
    }),
  );
}

test('sign-in page has one dominant signal lane, branded copy, and stacked form rhythm', async ({ page }) => {
  await page.goto('/login');

  const lane = page.getByTestId('auth-signal-lane');
  await expect(lane).toBeVisible();
  await expect(page.locator('[data-testid="auth-signal-lane"]')).toHaveCount(1);
  await expect(page.getByRole('heading', { name: /briefs become memory\./i })).toBeVisible();
  await expect(page.getByText(/one login\.\s*steady reading momentum\./i)).toBeVisible();
  await expectStackedForm(page, ['input[name="email"]', 'input[name="password"]', 'button[type="submit"]']);
  await expect(page.getByRole('button', { name: /continue with google/i })).toHaveCSS(
    'background-color',
    'rgb(45, 114, 210)',
  );
});

test('sign-up page keeps one dominant signal lane, branded copy, and stacked form rhythm', async ({ page }) => {
  await page.goto('/signup');

  const lane = page.getByTestId('auth-signal-lane');
  await expect(lane).toBeVisible();
  await expect(page.locator('[data-testid="auth-signal-lane"]')).toHaveCount(1);
  await expect(page.getByRole('heading', { name: /build your reading ritual\./i })).toBeVisible();
  await expect(page.getByText(/save what matters, then come back to it with less friction\./i)).toBeVisible();
  await expectStackedForm(page, [
    'input[name="email"]',
    'input[name="password"]',
    'input[name="confirm"]',
    'button[type="submit"]',
  ]);

  const ctaColor = await page.getByRole('button', { name: /create account/i }).evaluate((el) => {
    return getComputedStyle(el).backgroundColor;
  });
  expect(ctaColor).not.toBe('rgb(185, 139, 36)');
});

test('forgot-password page keeps one dominant signal lane, branded copy, and stacked form rhythm', async ({ page }) => {
  await page.goto('/forgot-password');

  const lane = page.getByTestId('auth-signal-lane');
  await expect(lane).toBeVisible();
  await expect(page.locator('[data-testid="auth-signal-lane"]')).toHaveCount(1);
  await expect(page.getByRole('heading', { name: /reset and return\./i })).toBeVisible();
  await expect(page.getByText(/we'll send a reset link\./i)).toBeVisible();
  await expectStackedForm(page, ['input[name="email"]', 'button[type="submit"]']);
  await expect(page.getByRole('button', { name: /send reset link/i })).toHaveCSS(
    'background-color',
    'rgb(45, 114, 210)',
  );
});

test('sign-in primary controls keep a visible keyboard focus ring', async ({ page }) => {
  await page.goto('/login');

  const emailInput = page.locator('input[name="email"]');
  const submitButton = page.getByRole('button', { name: /sign in with email/i });

  await emailInput.focus();
  await expect(emailInput).toBeFocused();
  await expect(emailInput).toHaveCSS('outline-offset', '2px');
  expect(await emailInput.evaluate((el) => getComputedStyle(el).boxShadow)).not.toBe('none');

  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  await expect(submitButton).toBeFocused();
  await expect(submitButton).toHaveCSS('outline-offset', '2px');
  expect(await submitButton.evaluate((el) => getComputedStyle(el).boxShadow)).not.toBe('none');
});
