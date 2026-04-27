import {
  AuthTokens,
  AuthStatus,
  GoogleLoginRequest,
  GoogleLoginResponse,
  EmailPasswordLoginRequest,
  EmailPasswordLoginResponse,
} from './types';
import { storageManager } from './storage';
import { resolveApiBaseUrl } from './runtime-config';

const ACCESS_TOKEN_EXPIRY_BUFFER = 5 * 60 * 1000; // 5 minutes buffer

export class AuthManager {
  private tokens: AuthTokens | null = null;
  private refreshPromise: Promise<AuthTokens> | null = null;

  async initialize(): Promise<void> {
    this.tokens = await storageManager.getTokens();
    this.refreshPromise = null;
  }

  async isAuthenticated(): Promise<boolean> {
    // Read from storage directly — avoids race with in-memory initialize()
    const tokens = await storageManager.getTokens();
    if (!tokens) return false;
    return Date.now() < tokens.expires_at;
  }

  async getAuthStatus(): Promise<AuthStatus | null> {
    try {
      const tokens = await storageManager.getTokens();
      if (!tokens) return { is_authenticated: false };

      // Local expiry check first — avoid a network round-trip for clearly expired tokens
      if (Date.now() >= tokens.expires_at) {
        try {
          await this.refreshToken();
        } catch {
          return { is_authenticated: false };
        }
      }

      try {
        const token = await this.getAccessToken();
        const apiBaseUrl = await this.getApiBaseUrl();
        const response = await fetch(`${apiBaseUrl}/api/v1/auth/status`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (response.ok) {
          return await response.json();
        }
        if (response.status === 401) {
          return { is_authenticated: false };
        }
        // Non-401 server error — fall through to local check
      } catch {
        // Network unavailable — fall back to local token validity
      }

      // Offline / transient server error: trust local token if not expired
      const fresh = await storageManager.getTokens();
      if (fresh && Date.now() < fresh.expires_at) {
        return { is_authenticated: true };
      }
      return { is_authenticated: false };
    } catch (error) {
      console.error('Error getting auth status:', error);
      return { is_authenticated: false };
    }
  }

  async getAccessToken(): Promise<string> {
    const storedTokens = await storageManager.getTokens();
    if (!storedTokens) {
      throw new Error('No tokens available');
    }

    // Check if token needs refresh (with buffer)
    if (Date.now() >= storedTokens.expires_at - ACCESS_TOKEN_EXPIRY_BUFFER) {
      const refreshed = await this.refreshToken();
      return refreshed.access_token;
    }

    return storedTokens.access_token;
  }

  async refreshToken(): Promise<AuthTokens> {
    // Deduplicate concurrent refresh calls
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    const tokens = await storageManager.getTokens();
    if (!tokens || !tokens.refresh_token) {
      throw new Error('No refresh token available');
    }

    const apiBaseUrl = await this.getApiBaseUrl();

    this.refreshPromise = (async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: tokens.refresh_token })
        });

        if (!response.ok) {
          // Server explicitly rejected the refresh token — credentials are invalid
          if (response.status === 401 || response.status === 403) {
            await storageManager.clearTokens();
            this.tokens = null;
          }
          throw new Error('Token refresh failed');
        }

        const data = await response.json();
        const newTokens: AuthTokens = {
          access_token: data.access_token,
          refresh_token: data.refresh_token || tokens.refresh_token,
          expires_at: new Date(data.expires_at).getTime(),
        };

        await storageManager.storeTokens(newTokens);
        this.tokens = newTokens;
        return newTokens;
      } catch (error) {
        // Network / transient error: preserve existing tokens
        if ((error as Error).message !== 'Token refresh failed') {
          console.error('Transient refresh error — tokens preserved:', error);
        }
        throw error;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  async loginWithGoogle(idToken: string, userInfo: GoogleLoginRequest['google_user_info']): Promise<void> {
    const apiBaseUrl = await this.getApiBaseUrl();

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          google_id_token: idToken,
          google_user_info: userInfo,
        })
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data: GoogleLoginResponse = await response.json();
      const tokens: AuthTokens = {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        expires_at: new Date(data.expires_at).getTime(),
      };

      await storageManager.storeTokens(tokens);
      this.tokens = tokens;
    } catch (error) {
      console.error('Error logging in with Google:', error);
      throw error;
    }
  }

  async loginWithEmailPassword(email: string, password: string): Promise<EmailPasswordLoginResponse> {
    const apiBaseUrl = await this.getApiBaseUrl();

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Login failed');
      }

      const data: EmailPasswordLoginResponse = await response.json();
      const tokens: AuthTokens = {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        expires_at: new Date(data.expires_at).getTime(),
      };

      await storageManager.storeTokens(tokens);
      this.tokens = tokens;
      return data;
    } catch (error) {
      console.error('Error logging in with email/password:', error);
      throw error;
    }
  }

  async logout(): Promise<void> {
    const apiBaseUrl = await this.getApiBaseUrl();

    try {
      const token = await storageManager.getTokens();
      if (token?.access_token) {
        await fetch(`${apiBaseUrl}/api/v1/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token.access_token}` }
        });
      }
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      await storageManager.clearTokens();
      this.tokens = null;
    }
  }

  private async getApiBaseUrl(): Promise<string> {
    const settings = await storageManager.getSettings();
    return resolveApiBaseUrl(settings.apiBaseUrl);
  }
}

export const authManager = new AuthManager();
