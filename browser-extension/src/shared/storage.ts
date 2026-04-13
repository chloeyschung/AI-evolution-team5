import { AuthTokens, ExtensionSettings, DEFAULT_SETTINGS } from './types';

const STORAGE_KEYS = {
  TOKENS: 'briefly_tokens',
  SETTINGS: 'briefly_settings',
} as const;

export class StorageManager {
  // Auth Tokens
  async getTokens(): Promise<AuthTokens | null> {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.TOKENS);
      return result[STORAGE_KEYS.TOKENS] || null;
    } catch (error) {
      console.error('Error getting tokens:', error);
      return null;
    }
  }

  async storeTokens(tokens: AuthTokens): Promise<void> {
    try {
      await chrome.storage.local.set({ [STORAGE_KEYS.TOKENS]: tokens });
    } catch (error) {
      console.error('Error storing tokens:', error);
      throw error;
    }
  }

  async clearTokens(): Promise<void> {
    try {
      await chrome.storage.local.remove(STORAGE_KEYS.TOKENS);
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
