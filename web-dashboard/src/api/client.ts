import axios, { type AxiosRequestConfig, type AxiosResponse, type AxiosError } from 'axios';
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '../types';

// Define types compatible with axios 1.x
type AxiosInstance = {
  (config: AxiosRequestConfig<any>): Promise<AxiosResponse<any>>;
  (url: string, config?: AxiosRequestConfig<any>): Promise<AxiosResponse<any>>;
  get<T = any>(url: string, config?: AxiosRequestConfig<any>): Promise<AxiosResponse<T>>;
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig<any>): Promise<AxiosResponse<T>>;
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig<any>): Promise<AxiosResponse<T>>;
  delete<T = any>(url: string, config?: AxiosRequestConfig<any>): Promise<AxiosResponse<T>>;
  interceptors: {
    request: { use: (onFulfilled: (config: AxiosRequestConfig) => AxiosRequestConfig | Promise<AxiosRequestConfig>) => void };
    response: { use: (onFulfilled: (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>) => void };
  };
};

let apiClient: AxiosInstance | null = null;
let refreshPromise: Promise<void> | null = null;
let currentAbortController: AbortController | null = null;

export function setAbortController(controller: AbortController | null): void {
  currentAbortController = controller;
}

function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
}

export function getApiClient(): AxiosInstance {
  if (!apiClient) {
    apiClient = axios.create({
      baseURL: getApiBaseUrl(),
      timeout: 10000, // 10 second timeout
      headers: {
        'Content-Type': 'application/json',
      },
      // Use AbortSignal for cancellation
      signal: currentAbortController?.signal,
    }) as AxiosInstance;

    // Request interceptor for auth token
    apiClient.interceptors.request.use(
      (config: AxiosRequestConfig) => {
        const token = localStorage.getItem(ACCESS_TOKEN_KEY);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        if (currentAbortController) {
          config.signal = currentAbortController.signal;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for token refresh with deduplication
    apiClient.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status !== 401) {
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
              window.location.href = '/login';
            }
            return Promise.reject(error);
          }
        }

        if (error.config) {
          const token = localStorage.getItem(ACCESS_TOKEN_KEY);
          if (token) {
            error.config.headers.Authorization = `Bearer ${token}`;
            return apiClient.request(error.config);
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
