import { authManager } from '../shared/auth';
import { apiClient } from '../shared/api';
import { storageManager } from '../shared/storage';
import type { AuthStatus, PageMetadata } from '../shared/types';
import { getRuntimeConfig } from '../shared/runtime-config';

const loadingEl = document.getElementById('loading') as HTMLDivElement;
const loggedOutEl = document.getElementById('logged-out') as HTMLDivElement;
const loggedInEl = document.getElementById('logged-in') as HTMLDivElement;
const errorEl = document.getElementById('error') as HTMLDivElement;
const errorMessageEl = document.getElementById('error-message') as HTMLParagraphElement;

const loginBtn = document.getElementById('login-btn') as HTMLButtonElement;
const emailLoginForm = document.getElementById('email-login-form') as HTMLFormElement;
const emailLoginBtn = document.getElementById('email-login-btn') as HTMLButtonElement;
const emailInput = document.getElementById('email-input') as HTMLInputElement;
const passwordInput = document.getElementById('password-input') as HTMLInputElement;
const saveCurrentPageBtn = document.getElementById('save-current-page') as HTMLButtonElement;
const openDashboardBtn = document.getElementById('open-dashboard') as HTMLButtonElement;
const recentListEl = document.getElementById('recent-list') as HTMLUListElement;
const logoutBtn = document.getElementById('logout-btn') as HTMLButtonElement;
const retryBtn = document.getElementById('retry-btn') as HTMLButtonElement;
const userEmailEl = document.getElementById('user-email') as HTMLSpanElement;
const apiUrlEl = document.getElementById('api-url') as HTMLInputElement;
const apiUrlSettingEl = document.getElementById('api-url-setting') as HTMLDivElement;
const settingsEl = document.querySelector('.settings') as HTMLDivElement;

let currentTab: chrome.tabs.Tab | null = null;

async function init(): Promise<void> {
  showLoading();

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTab = tab;

    await authManager.initialize();
    const authStatus = await authManager.getAuthStatus();

    if (authStatus?.is_authenticated) {
      showLoggedIn(authStatus);
    } else {
      showLoggedOut();
    }
  } catch (error) {
    console.error('Error initializing popup:', error);
    showError(error instanceof Error ? error.message : 'Failed to initialize extension. Please retry.');
  }
}

function showLoading(): void {
  loadingEl.classList.remove('hidden');
  loggedOutEl.classList.add('hidden');
  loggedInEl.classList.add('hidden');
  errorEl.classList.add('hidden');
}

function showLoggedOut(): void {
  loadingEl.classList.add('hidden');
  loggedOutEl.classList.remove('hidden');
  loggedInEl.classList.add('hidden');
  errorEl.classList.add('hidden');
}

function showLoggedIn(authStatus: AuthStatus): void {
  loadingEl.classList.add('hidden');
  loggedOutEl.classList.add('hidden');
  loggedInEl.classList.remove('hidden');
  errorEl.classList.add('hidden');

  userEmailEl.textContent = authStatus.email || 'Signed in';
  void loadSettings();
  void loadRecentContent();
}

function showError(message: string): void {
  loadingEl.classList.add('hidden');
  loggedOutEl.classList.add('hidden');
  loggedInEl.classList.add('hidden');
  errorEl.classList.remove('hidden');
  errorMessageEl.textContent = message;
}

async function loadSettings(): Promise<void> {
  const settings = await storageManager.getSettings();
  apiUrlEl.value = settings.apiBaseUrl;
  const showApiSetting = getRuntimeConfig().SHOW_API_URL_SETTING;
  apiUrlSettingEl.style.display = showApiSetting ? 'block' : 'none';
  settingsEl.style.display = showApiSetting ? 'grid' : 'none';
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function loadRecentContent(): Promise<void> {
  try {
    const items = await apiClient.getRecentContent(5);
    if (!items.length) {
      recentListEl.innerHTML = '<li class="recent-empty">No recent saves yet.</li>';
      return;
    }

    recentListEl.innerHTML = items
      .map((item) => {
        const title = escapeHtml(item.title || item.url || 'Untitled');
        const url = escapeHtml(item.url);
        const meta = escapeHtml(item.platform || 'web');
        return `<li><a class="recent-item" href="${url}" target="_blank" rel="noopener noreferrer"><span class="recent-item-title">${title}</span><span class="recent-item-meta">${meta}</span></a></li>`;
      })
      .join('');
  } catch {
    recentListEl.innerHTML = '<li class="recent-empty">Could not load recent saves.</li>';
  }
}

function deriveDashboardUrl(apiBaseUrl: string): string {
  const fallback = 'http://localhost:3001';
  const configured = apiBaseUrl.trim();
  if (!configured) return fallback;

  try {
    const parsed = new URL(configured);
    if (parsed.port === '8000') parsed.port = '3001';
    if (parsed.hostname === '127.0.0.1' && !parsed.port) parsed.port = '3001';
    if (parsed.hostname === 'localhost' && !parsed.port) parsed.port = '3001';
    parsed.pathname = '';
    parsed.search = '';
    parsed.hash = '';
    return parsed.toString().replace(/\/$/, '');
  } catch {
    return fallback;
  }
}

// Google login — uses chromiumapp.org redirect (Chrome intercepts it automatically,
// no Google Cloud Console registration required for this URI pattern).
loginBtn.addEventListener('click', async () => {
  try {
    const clientId = getRuntimeConfig().GOOGLE_CLIENT_ID || '';

    if (!clientId) {
      showError('Google Client ID is not configured.');
      return;
    }

    // Chrome intercepts redirects to https://<ext-id>.chromiumapp.org/ in
    // launchWebAuthFlow — no Console registration needed.
    const redirectUri = `https://${chrome.runtime.id}.chromiumapp.org/`;

    const authUrl =
      `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${clientId}&` +
      `redirect_uri=${encodeURIComponent(redirectUri)}&` +
      `response_type=code&` +
      `scope=openid%20email%20profile&` +
      `include_granted_scopes=true&` +
      `access_type=offline&` +
      `prompt=consent`;

    let redirectedUrl: string;
    try {
      const result = await chrome.identity.launchWebAuthFlow({ url: authUrl, interactive: true });
      if (!result) {
        throw new Error('No redirect URL received from Google.');
      }
      redirectedUrl = result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      // User dismissed the window — treat as silent cancellation
      if (
        msg.includes('closed') ||
        msg.includes('did not approve') ||
        msg.includes('cancelled') ||
        msg.includes('canceled')
      ) {
        return;
      }
      throw new Error(`Google sign-in failed: ${msg}`);
    }

    // Extract auth code from the redirect URL Chrome resolved with
    const codeUrl = new URL(redirectedUrl);
    const code = codeUrl.searchParams.get('code');
    if (!code) {
      throw new Error('No authorization code received from Google.');
    }

    // Exchange code for Briefly tokens via backend
    await authManager.loginWithGoogleCode(code, redirectUri);

    const authStatus = await authManager.getAuthStatus();
    if (authStatus?.is_authenticated) {
      showLoggedIn(authStatus);
      return;
    }

    throw new Error('Login did not complete. Please try again.');
  } catch (error) {
    console.error('Login error:', error);
    showError(error instanceof Error ? error.message : 'Login failed. Please try again.');
  }
});

// Email/password login
emailLoginForm.addEventListener('submit', async (e: Event) => {
  e.preventDefault();

  try {
    emailLoginBtn.disabled = true;
    emailLoginBtn.textContent = 'Signing in…';

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
      throw new Error('Please enter both email and password');
    }

    await authManager.loginWithEmailPassword(email, password);

    const authStatus = await authManager.getAuthStatus();
    if (authStatus?.is_authenticated) {
      showLoggedIn(authStatus);
      return;
    }

    throw new Error('Login did not complete. Please try again.');
  } catch (error) {
    console.error('Email login error:', error);
    showError(error instanceof Error ? error.message : 'Sign in failed. Please check your credentials.');
  } finally {
    emailLoginBtn.disabled = false;
    emailLoginBtn.textContent = 'Sign in with email';
  }
});

async function getActiveTabMetadata(): Promise<PageMetadata> {
  const [activeTab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  currentTab = activeTab ?? null;

  if (!currentTab?.id || !currentTab.url) {
    throw new Error('No active page to save.');
  }

  // chrome-extension:// and chrome:// pages cannot receive messages
  if (currentTab.url.startsWith('chrome') || currentTab.url.startsWith('about:')) {
    throw new Error('Cannot save browser internal pages.');
  }

  const liveTab = await chrome.tabs.get(currentTab.id);
  const liveUrl = liveTab.pendingUrl || liveTab.url || currentTab.url;
  if (!liveUrl) {
    throw new Error('No active page URL to save.');
  }

  try {
    const response = await chrome.tabs.sendMessage(currentTab.id, { action: 'getMetadata' });
    if (response?.metadata) {
      const metadata = response.metadata as PageMetadata;
      return {
        ...metadata,
        // Use live tab URL at save-time to avoid stale SPA metadata URL.
        url: liveUrl,
        title: metadata.title ?? liveTab.title ?? currentTab.title ?? null,
      };
    }
    throw new Error('No metadata from content script.');
  } catch {
    // Content script not yet injected — fall back to tab info
    return {
      url: liveUrl,
      title: liveTab.title ?? currentTab.title ?? null,
      author: null,
      description: null,
      type: 'unknown',
    };
  }
}

// Save content
saveCurrentPageBtn.addEventListener('click', async () => {
  if (!currentTab || !currentTab.url) {
    showError('No active page to save.');
    return;
  }

  try {
    saveCurrentPageBtn.disabled = true;
    saveCurrentPageBtn.textContent = 'Saving…';

    const metadata = await getActiveTabMetadata();
    await apiClient.shareContent(metadata);

    saveCurrentPageBtn.textContent = 'Saved';
    saveCurrentPageBtn.disabled = false;
    void loadRecentContent();
    setTimeout(() => {
      saveCurrentPageBtn.textContent = 'Save current page';
    }, 450);
  } catch (error) {
    console.error('Save error:', error);
    showError(error instanceof Error ? error.message : 'Failed to save content. Check API URL and retry.');
    saveCurrentPageBtn.textContent = 'Save current page';
    saveCurrentPageBtn.disabled = false;
  }
});

// Logout
logoutBtn.addEventListener('click', async () => {
  try {
    await authManager.logout();
    showLoggedOut();
  } catch (error) {
    console.error('Logout error:', error);
    showError('Failed to logout. Retry in a moment.');
  }
});

openDashboardBtn.addEventListener('click', async () => {
  const settings = await storageManager.getSettings();
  const dashboardUrl = deriveDashboardUrl(settings.apiBaseUrl);
  await chrome.tabs.create({ url: dashboardUrl });
});

// Retry
retryBtn.addEventListener('click', () => {
  void init();
});

// Settings
apiUrlEl.addEventListener('blur', async () => {
  const url = apiUrlEl.value.trim();
  if (url) {
    await storageManager.updateSettings({ apiBaseUrl: url });
  }
});

void init();
