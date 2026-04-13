import { AuthTokens, AuthStatus, GoogleLoginRequest, GoogleLoginResponse } from './types';
import { storageManager } from './storage';
import { apiClient } from './api';

const ACCESS_TOKEN_EXPIRY_BUFFER = 5 * 60 * 1000; // 5 minutes buffer

export class AuthManager {
  private tokens: AuthTokens | null = null;

  async initialize(): Promise<void> {
    this.tokens = await storageManager.getTokens();
  }

  async isAuthenticated(): Promise<boolean> {
    if (!this.tokens) return false;
    return Date.now() < this.tokens.expires_at;
  }

  async getAuthStatus(): Promise<AuthStatus | null> {
    try {
      const tokens = await storageManager.getTokens();
      if (!tokens) return { is_authenticated: false };

      const token = await this.getAccessToken();
      const response = await fetch(`${this.getApiBaseUrl()}/api/v1/auth/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        return await response.json();
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
    const tokens = await storageManager.getTokens();
    if (!tokens || !tokens.refresh_token) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await fetch(`${this.getApiBaseUrl()}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: tokens.refresh_token })
      });

      if (!response.ok) {
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
      console.error('Error refreshing token:', error);
      await storageManager.clearTokens();
      this.tokens = null;
      throw error;
    }
  }

  async loginWithGoogle(idToken: string, userInfo: GoogleLoginRequest['google_user_info']): Promise<void> {
    try {
      const response = await fetch(`${this.getApiBaseUrl()}/api/v1/auth/google`, {
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

  async logout(): Promise<void> {
    try {
      const token = await storageManager.getTokens();
      if (token?.access_token) {
        await fetch(`${this.getApiBaseUrl()}/api/v1/auth/logout`, {
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

  private getApiBaseUrl(): string {
    const settings = storageManager.getSettings();
    return settings.then(s => s.apiBaseUrl);
  }
}

export const authManager = new AuthManager();
