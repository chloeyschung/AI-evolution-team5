import axios, { type AxiosRequestConfig, type AxiosResponse, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '../types';
import { navigate } from '../utils/navigation';

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
  const explicitBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim();
  if (explicitBaseUrl) {
    return explicitBaseUrl;
  }

  // In local dev, keep requests same-origin and let Vite proxy /api -> backend.
  if (import.meta.env.DEV) {
    return '';
  }

  // In prod, default to same origin unless explicitly overridden.
  return window.location.origin;
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
            localStorage.removeItem(ACCESS_TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
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
      const { access_token, refresh_token } = response.data;
      localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
    } finally {
      refreshPromise = null;
    }
  })();

  await refreshPromise;
}
