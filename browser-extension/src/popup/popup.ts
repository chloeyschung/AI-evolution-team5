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
const logoutBtn = document.getElementById('logout-btn') as HTMLButtonElement;
const retryBtn = document.getElementById('retry-btn') as HTMLButtonElement;
const userEmailEl = document.getElementById('user-email') as HTMLSpanElement;
const autoSummarizeEl = document.getElementById('auto-summarize') as HTMLInputElement;
const apiUrlEl = document.getElementById('api-url') as HTMLInputElement;
const apiUrlSettingEl = document.getElementById('api-url-setting') as HTMLDivElement;

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
  autoSummarizeEl.checked = settings.autoSummarize;
  apiUrlEl.value = settings.apiBaseUrl;
  apiUrlSettingEl.style.display = getRuntimeConfig().SHOW_API_URL_SETTING ? 'block' : 'none';
}

// Google login
loginBtn.addEventListener('click', async () => {
  try {
    const clientId = getRuntimeConfig().GOOGLE_CLIENT_ID || '';

    if (!clientId) {
      showError('Google Client ID is not configured.');
      return;
    }

    const authUrl =
      `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${clientId}&` +
      `redirect_uri=${encodeURIComponent(chrome.runtime.getURL('login/login.html'))}&` +
      `response_type=code&` +
      `scope=openid%20email%20profile&` +
      `include_granted_scopes=true&` +
      `access_type=offline&` +
      `prompt=consent`;

    const loginCompletePromise = new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        chrome.runtime.onMessage.removeListener(loginListener);
        reject(new Error('Login timeout'));
      }, 10000);

      const loginListener = (message: { action?: string }) => {
        if (message.action === 'loginComplete') {
          clearTimeout(timeout);
          chrome.runtime.onMessage.removeListener(loginListener);
          resolve();
        }
      };

      chrome.runtime.onMessage.addListener(loginListener);
    });

    await chrome.identity.launchWebAuthFlow({ url: authUrl, interactive: true }).catch((error) => {
      if (error && error.message !== 'User closed the window') {
        throw new Error('Login cancelled or failed');
      }
    });

    await loginCompletePromise.catch((error) => {
      console.warn('Login signal timeout, fallback to token check:', error);
    });

    await authManager.initialize();
    const tokens = await storageManager.getTokens();

    if (tokens && Date.now() < tokens.expires_at) {
      const authStatus = await authManager.getAuthStatus();
      if (authStatus?.is_authenticated) {
        showLoggedIn(authStatus);
        return;
      }
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
  if (!currentTab?.id || !currentTab.url) {
    throw new Error('No active page to save.');
  }

  // chrome-extension:// and chrome:// pages cannot receive messages
  if (currentTab.url.startsWith('chrome') || currentTab.url.startsWith('about:')) {
    throw new Error('Cannot save browser internal pages.');
  }

  try {
    const response = await chrome.tabs.sendMessage(currentTab.id, { action: 'getMetadata' });
    if (response?.metadata) return response.metadata as PageMetadata;
    throw new Error('No metadata from content script.');
  } catch {
    // Content script not yet injected — fall back to tab info
    return {
      url: currentTab.url,
      title: currentTab.title ?? null,
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
    setTimeout(() => {
      saveCurrentPageBtn.textContent = 'Save current page';
      saveCurrentPageBtn.disabled = false;
    }, 1600);
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

// Retry
retryBtn.addEventListener('click', () => {
  void init();
});

// Settings
autoSummarizeEl.addEventListener('change', async () => {
  await storageManager.updateSettings({ autoSummarize: autoSummarizeEl.checked });
});

apiUrlEl.addEventListener('blur', async () => {
  const url = apiUrlEl.value.trim();
  if (url) {
    await storageManager.updateSettings({ apiBaseUrl: url });
  }
});

void init();
