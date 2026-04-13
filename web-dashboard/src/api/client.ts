import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

let apiClient: AxiosInstance | null = null;

export function getApiClient(): AxiosInstance {
  if (!apiClient) {
    apiClient = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth token
    apiClient.interceptors.request.use(
      async (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('briefly_access_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for token refresh
    apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Attempt token refresh
          const refreshToken = localStorage.getItem('briefly_refresh_token');
          if (refreshToken) {
            try {
              const response = await axios.post(
                `${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/refresh`,
                { refresh_token: refreshToken }
              );
              const { access_token, refresh_token } = response.data;
              localStorage.setItem('briefly_access_token', access_token);
              localStorage.setItem('briefly_refresh_token', refresh_token);

              // Retry original request
              if (error.config && error.config.headers) {
                error.config.headers.Authorization = `Bearer ${access_token}`;
                return apiClient!.request(error.config);
              }
            } catch {
              // Refresh failed, redirect to login
              localStorage.removeItem('briefly_access_token');
              localStorage.removeItem('briefly_refresh_token');
              window.location.href = '/login';
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  return apiClient;
}
