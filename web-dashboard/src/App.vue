<script setup lang="ts">
import { computed } from 'vue';
import { RouterView } from 'vue-router';
import { useAuthStore } from './stores/auth';
import Header from './components/layout/Header.vue';

const authStore = useAuthStore();

const showHeader = computed(() => {
  const route = authStore.$state.currentRoute;
  return route?.name !== 'Login';
});
</script>

<template>
  <div id="app">
    <Header v-if="showHeader" />
    <main class="main-content">
      <RouterView />
    </main>
  </div>
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
