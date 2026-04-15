<script setup lang="ts">
import { onMounted } from 'vue';
import { useContentStore } from '../stores/content';
import ContentCard from '../components/content/ContentCard.vue';

const contentStore = useContentStore();

onMounted(async () => {
  contentStore.updateFilters({ status: 'inbox' });
  await contentStore.loadContent(1);
  await contentStore.loadPlatforms();
});

const handleDelete = async (id: number) => {
  try {
    await contentStore.deleteItem(id);
  } catch (error) {
    console.error('Delete failed:', error);
  }
};

const handleSwipe = async (action: { content_id: number; action: 'keep' | 'discard' }) => {
  try {
    await contentStore.performSwipe(action);
  } catch (error) {
    console.error('Swipe failed:', error);
  }
};
</script>

<template>
  <div class="inbox">
    <div class="page-header">
      <h1>Inbox</h1>
      <p>Content waiting to be processed</p>
    </div>

    <div class="filters">
      <label class="filter-label">
        Platform:
        <select
          v-model="contentStore.filters.platform"
          @change="contentStore.loadContent(1)"
          class="filter-select"
        >
          <option value="">All Platforms</option>
          <option
            v-for="platform in contentStore.platforms"
            :key="platform.platform"
            :value="platform.platform"
          >
            {{ platform.platform }} ({{ platform.count }})
          </option>
        </select>
      </label>
    </div>

    <div class="content-grid">
      <ContentCard
        v-for="item in contentStore.items"
        :key="item.id"
        :content="item"
        @delete="handleDelete"
        @swipe="handleSwipe"
      />
    </div>

    <div v-if="contentStore.isLoading" class="loading">
      Loading...
    </div>

    <div v-if="!contentStore.items.length && !contentStore.isLoading" class="empty">
      <p>Your inbox is empty! 🎉</p>
    </div>
  </div>
</template>

<style scoped>
.inbox {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.page-header p {
  color: var(--text-secondary);
  font-size: 16px;
}

.filters {
  margin-bottom: 24px;
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

.loading,
.empty {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
}
</style>
