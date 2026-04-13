<script setup lang="ts">
import { onMounted } from 'vue';
import { useContentStore } from '../stores/content';
import ContentCard from '../components/content/ContentCard.vue';

const contentStore = useContentStore();

onMounted(async () => {
  contentStore.updateFilters({ status: 'archived' });
  await contentStore.loadContent(1);
});
</script>

<template>
  <div class="archive">
    <div class="page-header">
      <h1>Archive</h1>
      <p>Your kept content library</p>
    </div>

    <div class="content-grid">
      <ContentCard
        v-for="item in contentStore.items"
        :key="item.id"
        :content="item"
      />
    </div>

    <div v-if="contentStore.isLoading" class="loading">
      Loading...
    </div>

    <div v-if="!contentStore.items.length && !contentStore.isLoading" class="empty">
      <p>No archived content yet. Keep some items from your inbox!</p>
    </div>
  </div>
</template>

<style scoped>
.archive {
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
