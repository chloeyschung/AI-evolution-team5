import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  getContent,
  getPendingContent,
  getKeptContent,
  getContentDetail,
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

export const useContentStore = defineStore('content', () => {
  // State
  const items = ref<Content[]>([]);
  const selectedIds = ref<Set<number>>(new Set());
  const filters = ref<ContentFilters>({
    status: 'all',
    platform: null,
    dateFrom: null,
    dateTo: null,
  });
  const sort = ref<ContentSort>({
    option: 'recency',
    order: 'desc',
  });
  const page = ref<number>(1);
  const hasMore = ref<boolean>(true);
  const platforms = ref<PlatformCount[]>([]);
  const searchQuery = ref<string>('');
  const isLoading = ref<boolean>(false);
  const error = ref<string | null>(null);

  // Computed
  const filteredItems = computed(() => {
    if (!searchQuery.value) return items.value;
    const query = searchQuery.value.toLowerCase();
    return items.value.filter((item) => {
      const title = item.title?.toLowerCase() || '';
      const author = item.author?.toLowerCase() || '';
      return title.includes(query) || author.includes(query);
    });
  });

  const selectedCount = computed(() => selectedIds.value.size);
  const allSelected = computed(() =>
    items.value.length > 0 && selectedIds.value.size === items.value.length
  );

  // Actions
  async function loadContent(
    newPage: number = 1,
    append: boolean = false
  ): Promise<void> {
    if (newPage < page.value && !append) return;

    isLoading.value = true;
    error.value = null;

    try {
      let newItems: Content[];

      if (filters.value.status === 'inbox') {
        newItems = await getPendingContent(DEFAULT_PAGE_SIZE, filters.value.platform || undefined);
      } else if (filters.value.status === 'archived') {
        newItems = await getKeptContent(DEFAULT_PAGE_SIZE, (newPage - 1) * DEFAULT_PAGE_SIZE);
      } else {
        const result = await getContent(filters.value, sort.value, newPage, DEFAULT_PAGE_SIZE);
        newItems = result.items;
      }

      if (append) {
        items.value = [...items.value, ...newItems];
      } else {
        items.value = newItems;
      }

      page.value = newPage;
      hasMore.value = newItems.length === DEFAULT_PAGE_SIZE;
      selectedIds.value.clear();
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load content';
      console.error('Load content error:', err);
    } finally {
      isLoading.value = false;
    }
  }

  async function loadPlatforms(): Promise<void> {
    try {
      platforms.value = await getPlatforms();
    } catch (err) {
      console.error('Load platforms error:', err);
    }
  }

  async function performSearch(query: string): Promise<void> {
    searchQuery.value = query;
    if (!query) {
      await loadContent(1);
      return;
    }

    isLoading.value = true;
    try {
      const results = await searchContent(query, DEFAULT_PAGE_SIZE, 0);
      items.value = results;
      hasMore.value = results.length === DEFAULT_PAGE_SIZE;
      page.value = 1;
      selectedIds.value.clear();
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Search failed';
    } finally {
      isLoading.value = false;
    }
  }

  async function deleteItem(id: number): Promise<void> {
    try {
      await deleteContent(id);
      items.value = items.value.filter((item) => item.id !== id);
      selectedIds.value.delete(id);
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Delete failed';
      throw err;
    }
  }

  async function performSwipe(action: SwipeAction): Promise<void> {
    try {
      await recordSwipe(action);
      // Reload to update list
      await loadContent(page.value);
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Swipe failed';
      throw err;
    }
  }

  function toggleSelection(id: number): void {
    if (selectedIds.value.has(id)) {
      selectedIds.value.delete(id);
    } else {
      selectedIds.value.add(id);
    }
  }

  function toggleAllSelection(): void {
    if (allSelected.value) {
      selectedIds.value.clear();
    } else {
      items.value.forEach((item) => selectedIds.value.add(item.id));
    }
  }

  function clearSelection(): void {
    selectedIds.value.clear();
  }

  function updateFilters(newFilters: Partial<ContentFilters>): void {
    filters.value = { ...filters.value, ...newFilters };
    loadContent(1);
  }

  function updateSort(newSort: Partial<ContentSort>): void {
    sort.value = { ...sort.value, ...newSort };
    loadContent(1);
  }

  return {
    // State
    items,
    selectedIds,
    filters,
    sort,
    page,
    hasMore,
    platforms,
    searchQuery,
    isLoading,
    error,

    // Computed
    filteredItems,
    selectedCount,
    allSelected,

    // Actions
    loadContent,
    loadPlatforms,
    performSearch,
    deleteItem,
    performSwipe,
    toggleSelection,
    toggleAllSelection,
    clearSelection,
    updateFilters,
    updateSort,
  };
});
