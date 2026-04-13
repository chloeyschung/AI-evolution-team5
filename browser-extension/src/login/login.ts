import { storageManager } from '../shared/storage';

interface LoginResponse {
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
    const state = urlParams.get('state');

    if (!code) {
      throw new Error('Authorization code not found');
    }

    showLoading();

    // Get API base URL from storage
    const settings = await storageManager.getSettings();
    const apiBaseUrl = settings.apiBaseUrl;

    // Exchange code for tokens using the backend
    const tokenResponse = await fetch(`${apiBaseUrl}/api/v1/auth/google/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, state }),
    });

    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      throw new Error(errorData.detail || 'Token exchange failed');
    }

    const data: LoginResponse = await tokenResponse.json();

    // Store tokens
    await storageManager.storeTokens({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      expires_at: new Date(data.expires_at).getTime(),
    });

    // Close this window and return to extension
    window.close();

    // If window can't be closed, show success message
    setTimeout(() => {
      showSuccess();
    }, 1000);
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
    successDiv.style.cssText = 'display: flex; flex-direction: column; align-items: center;';

    const iconDiv = document.createElement('div');
    iconDiv.style.cssText = 'width: 64px; height: 64px; background: #10b981; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-bottom: 16px;';

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '32');
    svg.setAttribute('height', '32');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'white');
    svg.setAttribute('stroke-width', '3');

    const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    polyline.setAttribute('points', '20 6 9 17 4 12');
    svg.appendChild(polyline);

    iconDiv.appendChild(svg);
    successDiv.appendChild(iconDiv);

    const h2 = document.createElement('h2');
    h2.textContent = 'Login Successful!';
    h2.style.cssText = 'margin-bottom: 8px; color: #111827;';
    successDiv.appendChild(h2);

    const p = document.createElement('p');
    p.textContent = 'You can close this window and return to the extension.';
    p.style.cssText = 'color: #6b7280;';
    successDiv.appendChild(p);

    container.appendChild(successDiv);
  }
}

backBtn.addEventListener('click', () => {
  window.close();
});

// Start
handleLogin();
