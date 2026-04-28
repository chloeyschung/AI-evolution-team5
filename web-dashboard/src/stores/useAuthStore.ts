import { create } from 'zustand';
import { checkAuthStatus, logout, loginWithEmailPassword } from '../api/endpoints';
import type { AuthStatus, User } from '../types';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '../types';

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  initialize: () => Promise<void>;
  performLogin: (authData: AuthStatus) => void;
  loginWithEmail: (email: string, password: string) => Promise<void>;
  performLogout: () => Promise<void>;
  clearAuth: () => void;
  saveTokens: (accessToken: string, refreshToken: string, expiresAt?: string) => void;

  // Getters
  getUserEmail: () => string;
  getUserName: () => string;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  isLoading: true,

  // Getters
  getUserEmail: () => get().user?.email || '',
  getUserName: () => {
    const user = get().user;
    return user?.display_name || get().getUserEmail();
  },

  // Actions
  initialize: async () => {
    try {
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!token) {
        set({
          isAuthenticated: false,
          isLoading: false,
        });
        return;
      }

      const status: AuthStatus = await checkAuthStatus();
      set({
        isAuthenticated: status.is_authenticated,
      });

      if (status.is_authenticated && status.user_id && status.email) {
        set({
          user: {
            id: status.user_id,
            email: status.email,
          },
        });
      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      set({
        isAuthenticated: false,
        user: null,
      });
    } finally {
      set({ isLoading: false });
    }
  },

  loginWithEmail: async (email: string, password: string) => {
    const data = await loginWithEmailPassword(email, password);
    get().saveTokens(data.access_token, data.refresh_token, data.expires_at);
    set({
      user: { id: data.user_id, email: data.email },
      isAuthenticated: true,
    });
  },

  performLogin: (authData: AuthStatus) => {
    if (authData.user_id && authData.email) {
      set({
        user: {
          id: authData.user_id,
          email: authData.email,
          display_name: authData.email,
        },
        isAuthenticated: true,
      });
    } else {
      set({ isAuthenticated: true });
    }
  },

  performLogout: async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      get().clearAuth();
    }
  },

  clearAuth: () => {
    set({
      user: null,
      isAuthenticated: false,
    });
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem('briefly_expires_at');
  },

  saveTokens: (accessToken: string, refreshToken: string, expiresAt?: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    if (expiresAt) {
      localStorage.setItem('briefly_expires_at', String(new Date(expiresAt).getTime()));
    }
  },
}));
