import { create } from 'zustand';
import {
  getContent,
  deleteContent,
  recordSwipe,
  getPlatforms,
  searchContent,
} from '../api/endpoints';
import type {
  Content,
  PlatformCount,
  ContentFilters,
  ContentSort,
  SwipeAction,
} from '../types';
import { DEFAULT_PAGE_SIZE } from '../types';

interface ContentState {
  // State
  items: Content[];
  selectedIds: Set<number>;
  filters: ContentFilters;
  sort: ContentSort;
  page: number;
  hasMore: boolean;
  platforms: PlatformCount[];
  searchQuery: string;
  isLoading: boolean;
  error: string | null;

  // Getters (as functions)
  getFilteredItems: () => Content[];
  getSelectedCount: () => number;
  getAllSelected: () => boolean;

  // Actions
  loadContent: (newPage?: number, append?: boolean) => Promise<void>;
  loadPlatforms: () => Promise<void>;
  performSearch: (query: string) => Promise<void>;
  deleteItem: (id: number) => Promise<void>;
  performSwipe: (action: SwipeAction) => Promise<void>;
  toggleSelection: (id: number) => void;
  toggleAllSelection: () => void;
  clearSelection: () => void;
  updateFilters: (newFilters: Partial<ContentFilters>) => void;
  updateSort: (newSort: Partial<ContentSort>) => void;
}

export const useContentStore = create<ContentState>((set, get) => ({
  // Initial state
  items: [],
  selectedIds: new Set(),
  filters: {
    status: 'all',
    platform: null,
    dateFrom: null,
    dateTo: null,
  },
  sort: {
    option: 'recency',
    order: 'desc',
  },
  page: 1,
  hasMore: true,
  platforms: [],
  searchQuery: '',
  isLoading: false,
  error: null,

  // Getters (as functions)
  getFilteredItems: () => {
    const { items, searchQuery } = get();
    if (!searchQuery) return items;
    const query = searchQuery.toLowerCase();
    return items.filter((item) => {
      const title = item.title?.toLowerCase() || '';
      const author = item.author?.toLowerCase() || '';
      return title.includes(query) || author.includes(query);
    });
  },
  getSelectedCount: () => get().selectedIds.size,
  getAllSelected: () => {
    const { items, selectedIds } = get();
    return items.length > 0 && selectedIds.size === items.length;
  },

  // Actions
  loadContent: async (newPage = 1, append = false) => {
    const { page, filters } = get();
    if (newPage < page && !append) return;

    set({ isLoading: true, error: null });

    try {
      const { sort } = get();
      const result = await getContent(filters, sort, newPage, DEFAULT_PAGE_SIZE);
      const newItems = result.items;

      if (append) {
        const { items } = get();
        set({
          items: [...items, ...newItems],
        });
      } else {
        set({
          items: newItems,
        });
      }

      set({
        page: newPage,
        hasMore: newItems.length === DEFAULT_PAGE_SIZE,
        selectedIds: new Set(),
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to load content',
      });
      console.error('Load content error:', err);
    } finally {
      set({ isLoading: false });
    }
  },

  loadPlatforms: async () => {
    try {
      const platforms = await getPlatforms();
      set({ platforms });
    } catch (err) {
      console.error('Load platforms error:', err);
    }
  },

  performSearch: async (query: string) => {
    set({ searchQuery: query });
    if (!query) {
      await get().loadContent(1);
      return;
    }

    set({ isLoading: true });
    try {
      const results = await searchContent(query, DEFAULT_PAGE_SIZE, 0);
      set({
        items: results,
        hasMore: results.length === DEFAULT_PAGE_SIZE,
        page: 1,
        selectedIds: new Set(),
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Search failed',
      });
    } finally {
      set({ isLoading: false });
    }
  },

  deleteItem: async (id: number) => {
    try {
      await deleteContent(id);
      const { items, selectedIds } = get();
      const newSelectedIds = new Set(selectedIds);
      newSelectedIds.delete(id);
      set({
        items: items.filter((item) => item.id !== id),
        selectedIds: newSelectedIds,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Delete failed',
      });
      throw err;
    }
  },

  performSwipe: async (action: SwipeAction) => {
    try {
      await recordSwipe(action);
      // Reload to update list
      const { page } = get();
      await get().loadContent(page);
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Swipe failed',
      });
      throw err;
    }
  },

  toggleSelection: (id: number) => {
    const { selectedIds } = get();
    const newSelectedIds = new Set(selectedIds);
    if (newSelectedIds.has(id)) {
      newSelectedIds.delete(id);
    } else {
      newSelectedIds.add(id);
    }
    set({ selectedIds: newSelectedIds });
  },

  toggleAllSelection: () => {
    const { items, selectedIds, getAllSelected } = get();
    if (getAllSelected()) {
      set({ selectedIds: new Set() });
    } else {
      const newSelectedIds = new Set(items.map((item) => item.id));
      set({ selectedIds: newSelectedIds });
    }
  },

  clearSelection: () => {
    set({ selectedIds: new Set() });
  },

  updateFilters: (newFilters: Partial<ContentFilters>) => {
    const { filters } = get();
    const newFiltersMerged = { ...filters, ...newFilters };
    const hasChanged = Object.entries(newFiltersMerged).some(
      ([key, value]) => filters[key as keyof ContentFilters] !== value
    );
    set({ filters: newFiltersMerged });
    if (hasChanged) get().loadContent(1);
  },

  updateSort: (newSort: Partial<ContentSort>) => {
    const { sort } = get();
    const newSortMerged = { ...sort, ...newSort };
    const hasChanged = Object.entries(newSortMerged).some(
      ([key, value]) => sort[key as keyof ContentSort] !== value
    );
    set({ sort: newSortMerged });
    if (hasChanged) get().loadContent(1);
  },
}));
