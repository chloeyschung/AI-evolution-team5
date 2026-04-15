<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { useContentStore } from '../../stores/content';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const contentStore = useContentStore();

const searchQuery = ref('');

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: '📊' },
  { name: 'Inbox', path: '/inbox', icon: '📬' },
  { name: 'Archive', path: '/archive', icon: '📚' },
  { name: 'Analytics', path: '/analytics', icon: '📈' },
  { name: 'Settings', path: '/settings', icon: '⚙️' },
];

const isActive = (path: string) => route.path === path;

const handleLogout = async () => {
  await authStore.performLogout();
  router.push('/login');
};

// Debounced search
let searchTimeout: ReturnType<typeof setTimeout> | null = null;
const handleSearch = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }
  searchTimeout = setTimeout(() => {
    contentStore.performSearch(searchQuery.value);
  }, 300);
};
</script>

<template>
  <header class="header">
    <div class="header-left">
      <div class="logo" @click="router.push('/dashboard')">
        <span class="logo-icon">📚</span>
        <span class="logo-text">Briefly</span>
      </div>

      <nav class="nav">
        <a
          v-for="item in navItems"
          :key="item.path"
          :class="['nav-item', { active: isActive(item.path) }]"
          :href="item.path"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-text">{{ item.name }}</span>
        </a>
      </nav>
    </div>

    <div class="header-right">
      <div class="search-box">
        <input
          v-model="searchQuery"
          @input="handleSearch"
          type="text"
          placeholder="Search..."
          class="search-input"
        />
      </div>

      <div class="user-menu">
        <span class="user-email">{{ authStore.userEmail }}</span>
        <button @click="handleLogout" class="logout-btn">
          Logout
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 20px;
  color: var(--text-primary);
}

.logo-icon {
  font-size: 24px;
}

.nav {
  display: flex;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  text-decoration: none;
  color: var(--text-secondary);
  font-size: 14px;
  transition: all 0.2s;
}

.nav-item:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--primary-color);
  color: white;
}

.nav-icon {
  font-size: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-box {
  position: relative;
}

.search-input {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
  width: 240px;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color);
  width: 280px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-email {
  font-size: 14px;
  color: var(--text-secondary);
}

.logout-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}
</style>
