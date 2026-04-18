import { storageManager } from '../shared/storage';

interface GoogleTokenResponse {
  access_token: string;
  id_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
}

interface GoogleUserInfoResponse {
  id: string;
  email: string;
  name: string;
  given_name?: string;
  family_name?: string;
  picture?: string;
  email_verified: boolean;
}

interface BackendLoginResponse {
  access_token: string;
  refresh_token: string;
  expires_at: string;
  user: {
    id: string;
    email: string;
    name?: string;
    picture?: string;
  };
  is_new_user: boolean;
}

const loadingEl = document.getElementById('loading') as HTMLDivElement;
const errorEl = document.getElementById('error') as HTMLDivElement;
const errorMessageEl = document.getElementById('error-message') as HTMLParagraphElement;
const backBtn = document.getElementById('back-btn') as HTMLButtonElement;

async function handleLogin(): Promise<void> {
  try {
    // Get code from URL
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');

    if (!code) {
      throw new Error('Authorization code not found');
    }

    showLoading();

    // Get Google Client ID from environment
    const googleClientId = (window as any).__BRIEFLY_CONFIG?.GOOGLE_CLIENT_ID || '';
    if (!googleClientId) {
      throw new Error('Google Client ID not configured');
    }

    // Step 1: Exchange code for Google tokens (ID token)
    const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        code,
        client_id: googleClientId,
        client_secret: '', // Not needed for public client
        redirect_uri: chrome.runtime.getURL('login/login.html'),
        grant_type: 'authorization_code',
      }),
    });

    if (!tokenResponse.ok) {
      throw new Error('Failed to exchange authorization code');
    }

    const googleTokens: GoogleTokenResponse = await tokenResponse.json();

    // Step 2: Get user info from Google
    const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
      headers: { Authorization: `Bearer ${googleTokens.access_token}` },
    });

    if (!userInfoResponse.ok) {
      throw new Error('Failed to get user info');
    }

    const userInfo: GoogleUserInfoResponse = await userInfoResponse.json();

    // Step 3: Get API base URL from storage
    const settings = await storageManager.getSettings();
    const apiBaseUrl = settings.apiBaseUrl;

    // Step 4: Exchange Google ID token for backend tokens
    const backendResponse = await fetch(`${apiBaseUrl}/api/v1/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        google_id_token: googleTokens.id_token,
        google_user_info: {
          id: userInfo.id,
          email: userInfo.email,
          name: userInfo.name,
          picture: userInfo.picture,
        },
      }),
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Login failed');
    }

    const backendData: BackendLoginResponse = await backendResponse.json();

    // Step 5: Store tokens
    await storageManager.storeTokens({
      access_token: backendData.access_token,
      refresh_token: backendData.refresh_token,
      expires_at: new Date(backendData.expires_at).getTime(),
    });

    // Notify popup that login completed successfully
    try {
      chrome.runtime.sendMessage({ action: 'loginComplete' });
    } catch (err) {
      console.warn('Failed to send loginComplete message:', err);
    }

    // Close this window and return to extension
    window.close();

    // If window can't be closed, show success message
    setTimeout(showSuccess, 1000);
  } catch (error) {
    console.error('Login error:', error);
    showError(error instanceof Error ? error.message : 'Login failed');
  }
}

function showLoading(): void {
  loadingEl.classList.remove('hidden');
  errorEl.classList.add('hidden');
}

function showError(message: string): void {
  loadingEl.classList.add('hidden');
  errorEl.classList.remove('hidden');
  errorMessageEl.textContent = message;
}

function showSuccess(): void {
  const container = document.querySelector('.container') as HTMLDivElement;
  if (container) {
    container.innerHTML = '';

    const successDiv = document.createElement('div');
    successDiv.className = 'login-success';

    const iconDiv = document.createElement('div');
    iconDiv.className = 'login-success-icon';

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '32');
    svg.setAttribute('height', '32');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '3');

    const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    polyline.setAttribute('points', '20 6 9 17 4 12');
    svg.appendChild(polyline);

    iconDiv.appendChild(svg);
    successDiv.appendChild(iconDiv);

    const h2 = document.createElement('h2');
    h2.textContent = 'Login Successful!';
    h2.className = 'login-success-title';
    successDiv.appendChild(h2);

    const p = document.createElement('p');
    p.textContent = 'You can close this window and return to the extension.';
    p.className = 'login-success-copy';
    successDiv.appendChild(p);

    container.appendChild(successDiv);
  }
}

backBtn.addEventListener('click', () => {
  window.close();
});

// Start
handleLogin();
