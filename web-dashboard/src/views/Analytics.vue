<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getStats, getUserStatistics } from '../api/endpoints';
import { Stats, UserStatistics } from '../types';

const stats = ref<Stats>({ pending: 0, kept: 0, discarded: 0 });
const userStats = ref<UserStatistics>({
  total_swipes: 0,
  total_kept: 0,
  total_discarded: 0,
  retention_rate: 0,
  streak_days: 0,
  first_swipe_at: null,
  last_swipe_at: null,
});
const isLoading = ref(true);

onMounted(async () => {
  try {
    [stats.value, userStats.value] = await Promise.all([
      getStats(),
      getUserStatistics(),
    ]);
  } catch (error) {
    console.error('Failed to load stats:', error);
  } finally {
    isLoading.value = false;
  }
});

const totalContent = () => stats.value.pending + stats.value.kept + stats.value.discarded;
</script>

<template>
  <div class="analytics">
    <div class="page-header">
      <h1>Analytics</h1>
      <p>Your reading insights and statistics</p>
    </div>

    <div v-if="isLoading" class="loading">Loading...</div>

    <div v-else class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ totalContent() }}</div>
        <div class="stat-label">Total Content</div>
      </div>

      <div class="stat-card pending">
        <div class="stat-value">{{ stats.pending }}</div>
        <div class="stat-label">In Inbox</div>
      </div>

      <div class="stat-card kept">
        <div class="stat-value">{{ stats.kept }}</div>
        <div class="stat-label">Archived</div>
      </div>

      <div class="stat-card discarded">
        <div class="stat-value">{{ stats.discarded }}</div>
        <div class="stat-label">Discarded</div>
      </div>
    </div>

    <div class="detailed-stats">
      <h2>Detailed Statistics</h2>

      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-item-label">Total Swipes</span>
          <span class="stat-item-value">{{ userStats.total_swipes }}</span>
        </div>

        <div class="stat-item">
          <span class="stat-item-label">Retention Rate</span>
          <span class="stat-item-value">
            {{ (userStats.retention_rate * 100).toFixed(1) }}%
          </span>
        </div>

        <div class="stat-item">
          <span class="stat-item-label">Current Streak</span>
          <span class="stat-item-value">{{ userStats.streak_days }} days</span>
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-item-label">First Swipe</span>
          <span class="stat-item-value">
            {{ userStats.first_swipe_at
              ? new Date(userStats.first_swipe_at).toLocaleDateString()
              : 'N/A'
            }}
          </span>
        </div>

        <div class="stat-item">
          <span class="stat-item-label">Last Swipe</span>
          <span class="stat-item-value">
            {{ userStats.last_swipe_at
              ? new Date(userStats.last_swipe_at).toLocaleDateString()
              : 'N/A'
            }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analytics {
  padding: 24px;
  max-width: 1000px;
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

.loading {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 48px;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.stat-card.pending .stat-value {
  color: #3b82f6;
}

.stat-card.kept .stat-value {
  color: #10b981;
}

.stat-card.discarded .stat-value {
  color: #f59e0b;
}

.detailed-stats {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
}

.detailed-stats h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 24px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
}

.stats-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.stat-item-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
