import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const readSource = (relativePath: string): string =>
  readFileSync(resolve(__dirname, '..', relativePath), 'utf8');

describe('web guidelines regression', () => {
  it('popup form controls include semantic name attributes', () => {
    const popupHtml = readSource('popup/popup.html');

    expect(popupHtml).toMatch(/id="api-url"[\s\S]*?name="apiBaseUrl"/);
  });

  it('motion and input affordances are present in extension styles', () => {
    const popupCss = readSource('popup/popup.css');
    const loginCss = readSource('login/login.css');
    const contentCss = readSource('content/content-script.css');

    expect(popupCss).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(loginCss).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(contentCss).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);

    expect(popupCss).toMatch(/\.btn\s*\{[\s\S]*?touch-action:\s*manipulation;/);
    expect(loginCss).toMatch(/\.btn\s*\{[\s\S]*?touch-action:\s*manipulation;/);
    expect(contentCss).toMatch(/\.briefly-save-button\s*\{[\s\S]*?touch-action:\s*manipulation;/);
    expect(contentCss).toMatch(/\.briefly-save-button:focus-visible\s*\{/);
  });

  it('decorative success icon and actionable popup fallbacks are explicit', () => {
    const loginTs = readSource('login/login.ts');
    const popupTs = readSource('popup/popup.ts');

    expect(loginTs).toMatch(/svg\.setAttribute\('aria-hidden',\s*'true'\)/);
    expect(popupTs).toContain('Failed to initialize extension. Please retry.');
    expect(popupTs).toContain('Login failed. Please try again.');
    expect(popupTs).toContain('Failed to save content. Check API URL and retry.');
    expect(popupTs).toContain('Failed to logout. Retry in a moment.');
  });
});
