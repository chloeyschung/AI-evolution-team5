// API Response Types

export interface Content {
  id: number;
  platform: string;
  content_type: string;
  url: string;
  title: string | null;
  author: string | null;
  summary: string | null;
  status: 'inbox' | 'archived';
  created_at: string;
  updated_at: string | null;
}

export interface SwipeAction {
  content_id: number;
  action: 'keep' | 'discard';
}

export interface AuthStatus {
  is_authenticated: boolean;
  user_id?: number;
  email?: string;
  token_expires_at?: string;
}

export interface User {
  id: number;
  email: string;
  display_name?: string | null;
  avatar_url?: string | null;
}

export interface PlatformCount {
  platform: string;
  count: number;
}

export interface Stats {
  pending: number;
  kept: number;
  discarded: number;
}

export interface UserStatistics {
  total_swipes: number;
  total_kept: number;
  total_discarded: number;
  retention_rate: number;
  streak_days: number;
  first_swipe_at: string | null;
  last_swipe_at: string | null;
}

// Filter & Sort Types

export type ContentStatus = 'inbox' | 'archived' | 'all';
export type SortOption = 'recency' | 'platform' | 'title';
export type SortOrder = 'asc' | 'desc';

export interface ContentFilters {
  status: ContentStatus;
  platform: string | null;
  dateFrom: string | null;
  dateTo: string | null;
}

export interface ContentSort {
  option: SortOption;
  order: SortOrder;
}

// View Types

export type ViewMode = 'grid' | 'list';

// Settings Types

export interface AppSettings {
  apiBaseUrl: string;
  theme: 'light' | 'dark' | 'system';
  defaultView: ViewMode;
  itemsPerPage: number;
}

export const DEFAULT_SETTINGS: AppSettings = {
  apiBaseUrl: 'http://localhost:8000',
  theme: 'system',
  defaultView: 'grid',
  itemsPerPage: 20,
};

// Storage keys
export const ACCESS_TOKEN_KEY = 'briefly_access_token';
export const REFRESH_TOKEN_KEY = 'briefly_refresh_token';

// Pagination constants
export const DEFAULT_PAGE_SIZE = 20;
