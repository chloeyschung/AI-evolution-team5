import { AuthTokens, ExtensionSettings, DEFAULT_SETTINGS } from './types';

const STORAGE_KEYS = {
  ACCESS_TOKEN: 'briefly_access_token',
  REFRESH_TOKEN: 'briefly_refresh_token',
  EXPIRES_AT: 'briefly_expires_at',
  SETTINGS: 'briefly_settings',
} as const;

export class StorageManager {
  // Auth Tokens - standardized keys to match web dashboard
  async getTokens(): Promise<AuthTokens | null> {
    try {
      const result = await chrome.storage.local.get([
        STORAGE_KEYS.ACCESS_TOKEN,
        STORAGE_KEYS.REFRESH_TOKEN,
        STORAGE_KEYS.EXPIRES_AT,
      ]);

      const access_token = result[STORAGE_KEYS.ACCESS_TOKEN];
      const refresh_token = result[STORAGE_KEYS.REFRESH_TOKEN];
      const expires_at = result[STORAGE_KEYS.EXPIRES_AT];

      if (!access_token || !refresh_token || !expires_at) {
        return null;
      }

      return { access_token, refresh_token, expires_at };
    } catch (error) {
      console.error('Error getting tokens:', error);
      return null;
    }
  }

  async storeTokens(tokens: AuthTokens): Promise<void> {
    try {
      await chrome.storage.local.set({
        [STORAGE_KEYS.ACCESS_TOKEN]: tokens.access_token,
        [STORAGE_KEYS.REFRESH_TOKEN]: tokens.refresh_token,
        [STORAGE_KEYS.EXPIRES_AT]: tokens.expires_at,
      });
    } catch (error) {
      console.error('Error storing tokens:', error);
      throw error;
    }
  }

  async clearTokens(): Promise<void> {
    try {
      await chrome.storage.local.remove([
        STORAGE_KEYS.ACCESS_TOKEN,
        STORAGE_KEYS.REFRESH_TOKEN,
        STORAGE_KEYS.EXPIRES_AT,
      ]);
    } catch (error) {
      console.error('Error clearing tokens:', error);
      throw error;
    }
  }

  // Settings
  async getSettings(): Promise<ExtensionSettings> {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
      return { ...DEFAULT_SETTINGS, ...result[STORAGE_KEYS.SETTINGS] };
    } catch (error) {
      console.error('Error getting settings:', error);
      return DEFAULT_SETTINGS;
    }
  }

  async updateSettings(settings: Partial<ExtensionSettings>): Promise<void> {
    try {
      const current = await this.getSettings();
      const updated = { ...current, ...settings };
      await chrome.storage.local.set({ [STORAGE_KEYS.SETTINGS]: updated });
    } catch (error) {
      console.error('Error updating settings:', error);
      throw error;
    }
  }

  async clearSettings(): Promise<void> {
    try {
      await chrome.storage.local.remove(STORAGE_KEYS.SETTINGS);
    } catch (error) {
      console.error('Error clearing settings:', error);
      throw error;
    }
  }
}

export const storageManager = new StorageManager();
