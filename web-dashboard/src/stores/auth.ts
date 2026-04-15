import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { checkAuthStatus, logout } from '../api/endpoints';
import type { AuthStatus, User } from '../types';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '../types';

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null);
  const isAuthenticated = ref<boolean>(false);
  const isLoading = ref<boolean>(true);

  // Computed
  const userEmail = computed(() => user.value?.email || '');
  const userName = computed(() => user.value?.display_name || userEmail.value);

  // Actions
  async function initialize(): Promise<void> {
    try {
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!token) {
        isAuthenticated.value = false;
        isLoading.value = false;
        return;
      }

      const status: AuthStatus = await checkAuthStatus();
      isAuthenticated.value = status.is_authenticated;

      if (status.is_authenticated && status.user_id && status.email) {
        user.value = {
          id: status.user_id,
          email: status.email,
        };
      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      isAuthenticated.value = false;
      user.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  function performLogin(authData: AuthStatus): void {
    if (authData.user_id && authData.email) {
      user.value = {
        id: authData.user_id,
        email: authData.email,
        display_name: authData.email,
      };
    }
    isAuthenticated.value = true;
  }

  async function performLogout(): Promise<void> {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearAuth();
    }
  }

  function clearAuth(): void {
    user.value = null;
    isAuthenticated.value = false;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  function saveTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }

  return {
    // State
    user,
    isAuthenticated,
    isLoading,

    // Computed
    userEmail,
    userName,

    // Actions
    initialize,
    performLogin,
    performLogout,
    clearAuth,
    saveTokens,
  };
});
