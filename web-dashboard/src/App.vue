<script setup lang="ts">
import { computed } from 'vue';
import { RouterView, useRoute } from 'vue-router';
import Header from './components/layout/Header.vue';
import ErrorBoundary from './components/ErrorBoundary.vue';

const route = useRoute();

const showHeader = computed(() => route.name !== 'Login' && route.name !== 'OAuthCallback');

const handleError = (error: Error) => {
  console.error('Global error:', error);
  // Could send to error tracking service here
};
</script>

<template>
  <ErrorBoundary :onError="handleError">
    <div id="app">
      <Header v-if="showHeader" />
      <main class="main-content">
        <RouterView />
      </main>
    </div>
  </ErrorBoundary>
</template>

<style scoped>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
}
</style>
