import axios, { type AxiosRequestConfig, type AxiosResponse, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '../types';
import { navigate } from '../utils/navigation';

// Registered by App.tsx to avoid circular import (client → store → endpoints → client)
let _onAuthExpired: (() => void) | null = null;
export function registerAuthExpiredHandler(fn: () => void): void {
  _onAuthExpired = fn;
}

let apiClient: ReturnType<typeof axios.create> | null = null;
let refreshPromise: Promise<void> | null = null;
let currentAbortController: AbortController | null = null;

function shouldSkip401Refresh(error: AxiosError): boolean {
  const url = error.config?.url ?? '';
  const authNoRefreshPaths = [
    '/api/v1/auth/login',
    '/api/v1/auth/google',
    '/api/v1/auth/google/code',
    '/api/v1/auth/register',
    '/api/v1/auth/verify-email',
    '/api/v1/auth/verify-email/resend',
    '/api/v1/auth/password-reset/request',
    '/api/v1/auth/password-reset/confirm',
  ];

  return authNoRefreshPaths.some((path) => url.includes(path));
}

export function setAbortController(controller: AbortController | null): void {
  currentAbortController = controller;
}

function getApiBaseUrl(): string {
  // 1. Build-time env var wins (CI / Docker deployments)
  const explicitBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim();
  if (explicitBaseUrl) return explicitBaseUrl;

  // 2. User-set override in Settings (allows pointing at a different backend at runtime)
  try {
    const raw = localStorage.getItem('briefly_settings');
    if (raw) {
      const stored = JSON.parse(raw).apiBaseUrl as string | undefined;
      if (stored && stored.trim()) return stored.trim();
    }
  } catch {
    // ignore corrupt localStorage
  }

  // 3. Local dev: empty string → Vite proxy forwards /api to backend
  if (import.meta.env.DEV) return '';

  // 4. Production: same origin
  return window.location.origin;
}

/**
 * Reset the cached API client instance.
 * Call this after updating apiBaseUrl in localStorage so the next request
 * picks up the new base URL.
 */
export function resetApiClient(): void {
  apiClient = null;
}

export function getApiClient(): ReturnType<typeof axios.create> {
  if (!apiClient) {
    apiClient = axios.create({
      baseURL: getApiBaseUrl(),
      timeout: 10000, // 10 second timeout
      headers: {
        'Content-Type': 'application/json',
      },
      // Use AbortSignal for cancellation
      signal: currentAbortController?.signal,
    });

    // Request interceptor for auth token
    apiClient.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem(ACCESS_TOKEN_KEY);
        if (token) {
          config.headers!.Authorization = `Bearer ${token}`;
        }
        if (currentAbortController) {
          config.signal = currentAbortController.signal;
        }
        return config;
      },
      (error: AxiosError) => Promise.reject(error)
    );

    // Response interceptor for token refresh with deduplication
    apiClient.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: AxiosError) => {
        if (error.response?.status !== 401 || shouldSkip401Refresh(error)) {
          return Promise.reject(error);
        }

        if (refreshPromise) {
          try {
            await refreshPromise;
          } catch {
            // Refresh failed, will redirect below
          }
        } else {
          try {
            refreshPromise = refreshAccessToken();
            await refreshPromise;
          } catch {
            refreshPromise = null;
            // Clear tokens AND update Zustand store so ProtectedRoute redirects immediately
            localStorage.removeItem(ACCESS_TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
            localStorage.removeItem('briefly_expires_at');
            _onAuthExpired?.();
            if (window.location.pathname !== '/login') {
              navigate('/login', { replace: true });
            }
            return Promise.reject(error);
          }
        }

        if (error.config) {
          const token = localStorage.getItem(ACCESS_TOKEN_KEY);
          if (token) {
            error.config.headers!.Authorization = `Bearer ${token}`;
            return apiClient!.request(error.config);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  return apiClient;
}

export async function refreshAccessToken(): Promise<void> {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const response = await axios.post(
        `${getApiBaseUrl()}/api/v1/auth/refresh`,
        { refresh_token: refreshToken }
      );
      const { access_token, refresh_token, expires_at } = response.data;
      localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
      if (expires_at) {
        localStorage.setItem('briefly_expires_at', String(new Date(expires_at).getTime()));
      }
    } finally {
      refreshPromise = null;
    }
  })();

  await refreshPromise;
}
