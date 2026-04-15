import { authManager, type AuthStatus } from '../shared/auth';
import { apiClient } from '../shared/api';
import { storageManager } from '../shared/storage';
import { pageExtractor } from '../utils/extractor';

// DOM Elements
const loadingEl = document.getElementById('loading') as HTMLDivElement;
const loggedOutEl = document.getElementById('logged-out') as HTMLDivElement;
const loggedInEl = document.getElementById('logged-in') as HTMLDivElement;
const errorEl = document.getElementById('error') as HTMLDivElement;
const errorMessageEl = document.getElementById('error-message') as HTMLParagraphElement;

const loginBtn = document.getElementById('login-btn') as HTMLButtonElement;
const saveCurrentPageBtn = document.getElementById('save-current-page') as HTMLButtonElement;
const logoutBtn = document.getElementById('logout-btn') as HTMLButtonElement;
const retryBtn = document.getElementById('retry-btn') as HTMLButtonElement;
const userEmailEl = document.getElementById('user-email') as HTMLSpanElement;
const autoSummarizeEl = document.getElementById('auto-summarize') as HTMLInputElement;
const apiUrlEl = document.getElementById('api-url') as HTMLInputElement;

// State
let currentTab: chrome.tabs.Tab | null = null;

// Initialize
async function init(): Promise<void> {
  showLoading();

  try {
    // Get current tab info
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTab = tab;

    // Initialize auth and check status
    await authManager.initialize();
    const authStatus = await authManager.getAuthStatus();

    if (authStatus?.is_authenticated) {
      showLoggedIn(authStatus);
    } else {
      showLoggedOut();
    }
  } catch (error) {
    console.error('Error initializing popup:', error);
    showError(error instanceof Error ? error.message : 'Failed to initialize');
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

function showLoggedIn(authStatus: { email?: string }): void {
  loadingEl.classList.add('hidden');
  loggedOutEl.classList.add('hidden');
  loggedInEl.classList.remove('hidden');
  errorEl.classList.add('hidden');

  userEmailEl.textContent = authStatus.email || 'Logged in';

  // Load settings
  loadSettings();
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
}

// Event Handlers
loginBtn.addEventListener('click', async () => {
  try {
    // Get Google Client ID from build-time config
    const client_id = (window as any).__BRIEFLY_CONFIG?.GOOGLE_CLIENT_ID || '';

    if (!client_id) {
      alert('Google Client ID not configured. Please update the extension configuration.');
      return;
    }

    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${client_id}&` +
      `redirect_uri=${encodeURIComponent(chrome.runtime.getURL('login/login.html'))}&` +
      `response_type=code&` +
      `scope=openid%20email%20profile&` +
      `include_granted_scopes=true&` +
      `access_type=offline&` +
      `prompt=consent`;

    // Set up listener for login completion signal
    const loginCompletePromise = new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => {
        chrome.runtime.onMessage.removeListener(loginListener);
        reject(new Error('Login timeout'));
      }, 10000); // 10 second timeout

      const loginListener = (message: { action?: string }) => {
        if (message.action === 'loginComplete') {
          clearTimeout(timeout);
          chrome.runtime.onMessage.removeListener(loginListener);
          resolve();
        }
      };

      chrome.runtime.onMessage.addListener(loginListener);
    });

    // Open OAuth flow - this returns when the window is closed
    await chrome.identity.launchWebAuthFlow({
      url: authUrl,
      interactive: true,
    }).catch((error) => {
      // User cancelled or flow failed
      if (error && error.message !== 'User closed the window') {
        throw new Error('Login cancelled or failed');
      }
    });

    // Wait for login completion signal from login.ts
    try {
      await loginCompletePromise;
    } catch (error) {
      // Timeout or error - fall back to checking tokens directly
      console.warn('Login signal timeout, checking tokens directly:', error);
    }

    // Check if login was successful by verifying tokens exist
    await authManager.initialize();
    const tokens = await storageManager.getTokens();

    if (tokens && Date.now() < tokens.expires_at) {
      // Login successful - get user info
      const authStatus = await authManager.getAuthStatus();
      if (authStatus?.is_authenticated) {
        showLoggedIn(authStatus);
        return;
      }
    }

    // If we get here, login failed
    throw new Error('Login did not complete. Please try again.');
  } catch (error) {
    console.error('Login error:', error);
    showError(error instanceof Error ? error.message : 'Login failed');
  }
});

saveCurrentPageBtn.addEventListener('click', async () => {
  if (!currentTab || !currentTab.url) {
    alert('No page to save');
    return;
  }

  try {
    saveCurrentPageBtn.disabled = true;
    saveCurrentPageBtn.textContent = 'Saving...';

    // Extract metadata from current page
    const metadata = await pageExtractor.extractMetadata();
    const selectedText = pageExtractor.getSelectedText();

    // Save content
    const result = await apiClient.shareContent(metadata, selectedText);

    // Show success with animation
    saveCurrentPageBtn.textContent = '✓ Saved!';
    saveCurrentPageBtn.classList.add('btn-success');

    setTimeout(() => {
      saveCurrentPageBtn.textContent = 'Save Current Page';
      saveCurrentPageBtn.classList.remove('btn-success');
      saveCurrentPageBtn.style.background = '';
      saveCurrentPageBtn.disabled = false;
    }, 2000);
  } catch (error) {
    console.error('Save error:', error);
    const errorMsg = error instanceof Error ? error.message : 'Failed to save content';

    // Show error state on button
    saveCurrentPageBtn.textContent = '✗ Error';
    saveCurrentPageBtn.style.background = '#dc2626';

    setTimeout(() => {
      saveCurrentPageBtn.textContent = 'Save Current Page';
      saveCurrentPageBtn.style.background = '';
      saveCurrentPageBtn.disabled = false;
    }, 2000);

    // Show error after button recovers
    setTimeout(() => {
      alert(errorMsg);
    }, 2200);
  }
});

logoutBtn.addEventListener('click', async () => {
  try {
    await authManager.logout();
    showLoggedOut();
  } catch (error) {
    console.error('Logout error:', error);
    showError('Failed to logout');
  }
});

retryBtn.addEventListener('click', init);

// Settings handlers
autoSummarizeEl.addEventListener('change', async () => {
  await storageManager.updateSettings({ autoSummarize: autoSummarizeEl.checked });
});

apiUrlEl.addEventListener('blur', async () => {
  const url = apiUrlEl.value.trim();
  if (url) {
    await storageManager.updateSettings({ apiBaseUrl: url });
  }
});

// Start
init();
