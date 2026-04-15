<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps<{
  onError?: (error: Error) => void;
}>();

const error = ref<Error | null>(null);
const hasError = ref(false);

// Global error handler
const errorHandler = (err: Error) => {
  error.value = err;
  hasError.value = true;
  if (props.onError) {
    props.onError(err);
  }
};

onMounted(() => {
  window.addEventListener('error', (event) => {
    errorHandler(event.error);
  });
  window.addEventListener('unhandledrejection', (event) => {
    errorHandler(event.reason as Error);
  });
});

onBeforeUnmount(() => {
  window.removeEventListener('error', errorHandler as any);
  window.removeEventListener('unhandledrejection', errorHandler as any);
});

const retry = () => {
  hasError.value = false;
  error.value = null;
  window.location.reload();
};
</script>

<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-container">
      <div class="error-icon">⚠️</div>
      <h1>Something went wrong</h1>
      <p class="error-message">{{ error?.message || 'An unexpected error occurred' }}</p>
      <button @click="retry" class="retry-btn">Reload Page</button>
    </div>
  </div>
  <div v-else>
    <slot />
  </div>
</template>

<style scoped>
.error-boundary {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 24px;
}

.error-container {
  text-align: center;
  max-width: 480px;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

h1 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.error-message {
  color: var(--text-secondary);
  margin-bottom: 24px;
  font-size: 14px;
}

.retry-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  background: var(--primary-color);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn:hover {
  background: var(--primary-hover);
}
</style>
