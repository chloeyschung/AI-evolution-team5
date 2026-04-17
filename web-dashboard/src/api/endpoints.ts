import { getApiClient } from './client';
import type {
  Content,
  AuthStatus,
  PlatformCount,
  Stats,
  UserStatistics,
  ContentFilters,
  ContentSort,
  SwipeAction,
} from '../types';

// Auth
export async function checkAuthStatus(): Promise<AuthStatus> {
  const client = getApiClient();
  const response = await client.get<AuthStatus>('/api/v1/auth/status');
  return response.data;
}

export async function loginWithGoogle(
  idToken: string,
  userInfo: { id: string; email: string; name?: string; picture?: string }
) {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/google', {
    google_id_token: idToken,
    google_user_info: userInfo,
  });
  return response.data;
}

export async function loginWithGoogleCode(code: string) {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/google/code', { code });
  return response.data;
}

export async function logout() {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/logout');
  return response.data;
}

export async function loginWithEmailPassword(email: string, password: string) {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/login', { email, password });
  return response.data as { access_token: string; refresh_token: string; expires_at: string; user_id: number; email: string };
}

export async function verifyEmail(token: string) {
  const client = getApiClient();
  const response = await client.get('/api/v1/auth/verify-email', { params: { token } });
  return response.data as { message: string };
}

export async function registerWithEmail(email: string, password: string) {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/register', { email, password });
  return response.data as { message: string };
}

export async function requestPasswordReset(email: string) {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/password-reset/request', { email });
  return response.data as { message: string };
}

export async function confirmPasswordReset(token: string, newPassword: string) {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/password-reset/confirm', {
    token,
    new_password: newPassword,
  });
  return response.data as { message: string };
}

export async function resendVerificationEmail(email: string) {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/verify-email/resend', { email });
  return response.data as { message: string };
}

// Content
export async function getContent(
  filters: ContentFilters,
  sort: ContentSort,
  page: number,
  limit: number
): Promise<{ items: Content[]; hasMore: boolean }> {
  const client = getApiClient();
  const params: Record<string, string | number> = {
    limit,
    offset: (page - 1) * limit,
  };

  if (filters.status && filters.status !== 'all') {
    params.status = filters.status;
  }
  if (filters.platform) {
    params.platform = filters.platform;
  }
  if (sort.option) {
    params.sort = sort.option;
  }
  if (sort.order) {
    params.order = sort.order;
  }

  const response = await client.get<Content[]>('/api/v1/content', { params });
  return {
    items: response.data,
    hasMore: response.data.length === limit,
  };
}

export async function getPendingContent(
  limit: number,
  platform?: string
): Promise<Content[]> {
  const client = getApiClient();
  const params: Record<string, string | number> = { limit };
  if (platform) params.platform = platform;

  const response = await client.get<Content[]>('/api/v1/content/pending', { params });
  return response.data;
}

export async function getKeptContent(limit: number, offset: number): Promise<Content[]> {
  const client = getApiClient();
  const response = await client.get<Content[]>('/api/v1/content/kept', {
    params: { limit, offset },
  });
  return response.data;
}

export async function getContentDetail(id: number): Promise<Content> {
  const client = getApiClient();
  const response = await client.get<Content>(`/api/v1/content/${id}`);
  return response.data;
}

export async function deleteContent(id: number): Promise<{ message: string }> {
  const client = getApiClient();
  const response = await client.delete<{ message: string }>(`/api/v1/content/${id}`);
  return response.data;
}

// Swipe
export async function recordSwipe(action: SwipeAction): Promise<{ id: number; content_id: number; action: string }> {
  const client = getApiClient();
  const response = await client.post('/api/v1/swipe', action);
  return response.data;
}

// Platforms
export async function getPlatforms(): Promise<PlatformCount[]> {
  const client = getApiClient();
  const response = await client.get<PlatformCount[]>('/api/v1/platforms');
  return response.data;
}

// Search
export async function searchContent(query: string, limit: number, offset: number): Promise<Content[]> {
  const client = getApiClient();
  const response = await client.get<Content[]>('/api/v1/search', {
    params: { q: query, limit, offset },
  });
  return response.data;
}

// Stats
export async function getStats(): Promise<Stats> {
  const client = getApiClient();
  const response = await client.get<Stats>('/api/v1/stats');
  return response.data;
}

export async function getUserStatistics(): Promise<UserStatistics> {
  const client = getApiClient();
  const response = await client.get<UserStatistics>('/api/v1/user/statistics');
  return response.data;
}
