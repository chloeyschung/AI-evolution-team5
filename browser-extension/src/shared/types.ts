// Briefly API Types

export interface ShareData {
  content: string;
  platform?: string;
  metadata?: Record<string, unknown>;
}

export interface ShareResponse {
  id: number;
  platform: string;
  content_type: string;
  url: string;
  title: string | null;
  author: string | null;
  summary: string | null;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_at: number; // Unix timestamp in milliseconds
}

export interface AuthStatus {
  is_authenticated: boolean;
  user_id?: number;
  email?: string;
  token_expires_at?: string;
}

export interface GoogleLoginRequest {
  google_id_token: string;
  google_user_info: {
    id: string;
    email: string;
    name?: string;
    picture?: string;
  };
}

export interface GoogleLoginResponse {
  access_token: string;
  refresh_token: string;
  expires_at: string;
  user: Record<string, unknown>;
  is_new_user: boolean;
}

export interface LogoutResponse {
  message: string;
}

// Extension Types

export interface PageMetadata {
  url: string;
  title: string | null;
  author: string | null;
  description: string | null;
  type: ContentType;
}

export type ContentType = 'article' | 'video' | 'social' | 'image' | 'text' | 'unknown';

export interface SaveRequest {
  metadata: PageMetadata;
  selectedText?: string;
}

export interface SaveResult {
  success: boolean;
  data?: ShareResponse;
  error?: string;
}

export interface Notification {
  type: 'success' | 'error' | 'info';
  message: string;
}

export interface ExtensionSettings {
  apiBaseUrl: string;
  autoSummarize: boolean;
}

export const DEFAULT_SETTINGS: ExtensionSettings = {
  apiBaseUrl: 'http://localhost:8000',
  autoSummarize: true,
};
