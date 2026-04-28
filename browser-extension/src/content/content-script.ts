import { pageExtractor } from '../utils/extractor';
import { PageMetadata } from '../shared/types';

// Listen for messages from background script or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'getMetadata') {
    handleGetMetadata().then(sendResponse);
    return true; // Keep channel open for async response
  }
  return false;
});

async function handleGetMetadata(): Promise<{ metadata: PageMetadata }> {
  // Always read live DOM + location to avoid stale metadata across SPA transitions.
  const metadata = await pageExtractor.extractMetadata();
  return { metadata };
}

// ─── Auth sync bridge ─────────────────────────────────────────────────────
// Bridges chrome.storage.local (extension) ↔ localStorage (web dashboard).
// Runs on every page — only has effect when localStorage tokens are present
// (i.e., on the dashboard's origin) or when extension tokens need to be
// injected into the current origin.

const AUTH_KEYS = {
  ACCESS_TOKEN: 'briefly_access_token',
  REFRESH_TOKEN: 'briefly_refresh_token',
  EXPIRES_AT: 'briefly_expires_at',
} as const;

function decodeJwtExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

async function syncExtensionToPage(): Promise<void> {
  const stored = await chrome.storage.local.get([
    AUTH_KEYS.ACCESS_TOKEN,
    AUTH_KEYS.REFRESH_TOKEN,
    AUTH_KEYS.EXPIRES_AT,
  ]);
  const extAccess = stored[AUTH_KEYS.ACCESS_TOKEN] as string | undefined;
  const extRefresh = stored[AUTH_KEYS.REFRESH_TOKEN] as string | undefined;
  const extExpires = stored[AUTH_KEYS.EXPIRES_AT] as number | undefined;

  if (!extAccess || !extRefresh) return;
  if (localStorage.getItem(AUTH_KEYS.ACCESS_TOKEN)) return; // page already has tokens

  localStorage.setItem(AUTH_KEYS.ACCESS_TOKEN, extAccess);
  localStorage.setItem(AUTH_KEYS.REFRESH_TOKEN, extRefresh);
  if (extExpires) {
    localStorage.setItem(AUTH_KEYS.EXPIRES_AT, String(extExpires));
  }
}

async function syncPageToExtension(): Promise<void> {
  const pageAccess = localStorage.getItem(AUTH_KEYS.ACCESS_TOKEN);
  const pageRefresh = localStorage.getItem(AUTH_KEYS.REFRESH_TOKEN);
  if (!pageAccess || !pageRefresh) return;

  const stored = await chrome.storage.local.get(AUTH_KEYS.ACCESS_TOKEN);
  if (stored[AUTH_KEYS.ACCESS_TOKEN]) return; // extension already has tokens

  const rawExpiry = localStorage.getItem(AUTH_KEYS.EXPIRES_AT);
  const expiresAt = rawExpiry
    ? parseInt(rawExpiry, 10)
    : (decodeJwtExpiry(pageAccess) ?? Date.now() + 3600 * 1000);

  await chrome.storage.local.set({
    [AUTH_KEYS.ACCESS_TOKEN]: pageAccess,
    [AUTH_KEYS.REFRESH_TOKEN]: pageRefresh,
    [AUTH_KEYS.EXPIRES_AT]: expiresAt,
  });
}

// page localStorage → extension: intercept setItem/removeItem since the
// `storage` event only fires in OTHER tabs, not in the writing tab itself.
// Capture originals FIRST — the onChanged handler uses these to avoid re-entrancy.
const _setItem = localStorage.setItem.bind(localStorage);
const _removeItem = localStorage.removeItem.bind(localStorage);

localStorage.setItem = function (key: string, value: string): void {
  _setItem(key, value);
  if (key === AUTH_KEYS.ACCESS_TOKEN || key === AUTH_KEYS.REFRESH_TOKEN) {
    const access = localStorage.getItem(AUTH_KEYS.ACCESS_TOKEN);
    const refresh = localStorage.getItem(AUTH_KEYS.REFRESH_TOKEN);
    if (access && refresh) {
      const rawExpiry = localStorage.getItem(AUTH_KEYS.EXPIRES_AT);
      const expiresAt = rawExpiry
        ? parseInt(rawExpiry, 10)
        : (decodeJwtExpiry(access) ?? Date.now() + 3600 * 1000);
      chrome.storage.local.set({
        [AUTH_KEYS.ACCESS_TOKEN]: access,
        [AUTH_KEYS.REFRESH_TOKEN]: refresh,
        [AUTH_KEYS.EXPIRES_AT]: expiresAt,
      });
    }
  }
  if (key === AUTH_KEYS.EXPIRES_AT) {
    chrome.storage.local.get(AUTH_KEYS.ACCESS_TOKEN).then((stored) => {
      if (stored[AUTH_KEYS.ACCESS_TOKEN]) {
        chrome.storage.local.set({ [AUTH_KEYS.EXPIRES_AT]: parseInt(value, 10) });
      }
    });
  }
};

localStorage.removeItem = function (key: string): void {
  _removeItem(key);
  if (key === AUTH_KEYS.ACCESS_TOKEN || key === AUTH_KEYS.REFRESH_TOKEN) {
    chrome.storage.local.remove([
      AUTH_KEYS.ACCESS_TOKEN,
      AUTH_KEYS.REFRESH_TOKEN,
      AUTH_KEYS.EXPIRES_AT,
    ]);
  }
};

// Initial sync on page load
syncExtensionToPage();
syncPageToExtension();

// extension storage → page: watch for login/logout in the extension.
// Uses _setItem/_removeItem (originals, captured above) — NOT the monkey-patched
// versions — to prevent re-entrancy: patched setItem → chrome.storage.set →
// onChanged → patched setItem → ... infinite loop + 429 rate-limit cascade.
chrome.storage.local.onChanged.addListener((changes) => {
  const access = changes[AUTH_KEYS.ACCESS_TOKEN];
  const refresh = changes[AUTH_KEYS.REFRESH_TOKEN];
  const expires = changes[AUTH_KEYS.EXPIRES_AT];

  if (access) {
    if (access.newValue) {
      _setItem(AUTH_KEYS.ACCESS_TOKEN, access.newValue as string);
    } else {
      _removeItem(AUTH_KEYS.ACCESS_TOKEN);
    }
  }
  if (refresh) {
    if (refresh.newValue) {
      _setItem(AUTH_KEYS.REFRESH_TOKEN, refresh.newValue as string);
    } else {
      _removeItem(AUTH_KEYS.REFRESH_TOKEN);
    }
  }
  if (expires) {
    if (expires.newValue) {
      _setItem(AUTH_KEYS.EXPIRES_AT, String(expires.newValue));
    } else {
      _removeItem(AUTH_KEYS.EXPIRES_AT);
    }
  }
});
