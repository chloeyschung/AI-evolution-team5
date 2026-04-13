<script setup lang="ts">
import { Content } from '../../types';

defineProps<{
  content: Content;
}>();

defineEmits<{
  (e: 'delete', id: number): void;
  (e: 'swipe', action: { content_id: number; action: 'keep' | 'discard' }): void;
}>();

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

const getPlatformIcon = (platform: string) => {
  const icons: Record<string, string> = {
    youtube: '📺',
    linkedin: '💼',
    twitter: '🐦',
    x: '🐦',
    medium: '✍️',
    instagram: '📷',
    facebook: '👍',
    tiktok: '🎵',
    reddit: '👽',
    web: '🌐',
  };
  return icons[platform.toLowerCase()] || '📄';
};
</script>

<template>
  <article class="content-card">
    <div class="card-header">
      <div class="platform-info">
        <span class="platform-icon">{{ getPlatformIcon(content.platform) }}</span>
        <span class="platform-name">{{ content.platform }}</span>
      </div>
      <div class="card-actions">
        <button class="action-btn keep-btn" title="Keep">
          ✓
        </button>
        <button class="action-btn discard-btn" title="Discard">
          ✕
        </button>
        <button class="action-btn delete-btn" title="Delete">
          🗑
        </button>
      </div>
    </div>

    <div class="card-content">
      <h3 class="card-title">
        {{ content.title || 'Untitled' }}
      </h3>

      <p v-if="content.author" class="card-author">
        by {{ content.author }}
      </p>

      <p v-if="content.summary" class="card-summary">
        {{ content.summary }}
      </p>
    </div>

    <div class="card-footer">
      <span class="card-date">{{ formatDate(content.created_at) }}</span>
      <span class="card-status" :class="content.status">
        {{ content.status === 'inbox' ? 'Inbox' : 'Archived' }}
      </span>
    </div>

    <a :href="content.url" target="_blank" rel="noopener noreferrer" class="card-link">
      Open original →
    </a>
  </article>
</template>

<style scoped>
.content-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: box-shadow 0.2s;
}

.content-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.platform-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.platform-icon {
  font-size: 18px;
}

.platform-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: capitalize;
}

.card-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.keep-btn {
  color: #10b981;
}

.keep-btn:hover {
  background: #10b981;
  color: white;
}

.discard-btn {
  color: #f59e0b;
}

.discard-btn:hover {
  background: #f59e0b;
  color: white;
}

.delete-btn {
  color: #ef4444;
}

.delete-btn:hover {
  background: #ef4444;
  color: white;
}

.card-content {
  flex: 1;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.card-author {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
}

.card-summary {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.card-date {
  font-size: 12px;
  color: var(--text-tertiary);
}

.card-status {
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.card-status.inbox {
  background: #dbeafe;
  color: #1d4ed8;
}

.card-status.archived {
  background: #d1fae5;
  color: #047857;
}

.card-link {
  display: block;
  text-align: center;
  padding: 12px;
  margin: -4px -20px -20px;
  background: var(--bg-tertiary);
  color: var(--primary-color);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  border-radius: 0 0 12px 12px;
  transition: background 0.2s;
}

.card-link:hover {
  background: var(--bg-secondary);
}
</style>
