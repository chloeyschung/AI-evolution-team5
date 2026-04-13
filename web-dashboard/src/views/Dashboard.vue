<script setup lang="ts">
import { onMounted } from 'vue';
import { useContentStore } from '../stores/content';
import ContentCard from '../components/content/ContentCard.vue';

const contentStore = useContentStore();

onMounted(async () => {
  await contentStore.loadContent(1);
  await contentStore.loadPlatforms();
});
</script>

<template>
  <div class="dashboard">
    <div class="page-header">
      <h1>Dashboard</h1>
      <p>Your knowledge library at a glance</p>
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
      <p>No content found. Save something from the mobile app or browser extension!</p>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
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
