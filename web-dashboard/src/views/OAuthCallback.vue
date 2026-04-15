<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { loginWithGoogleCode } from '../api/endpoints';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const isLoading = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
  try {
    const code = route.query.code as string;

    if (!code) {
      throw new Error('OAuth code missing');
    }

    // Send code to backend - it handles token exchange with client_secret
    const authData = await loginWithGoogleCode(code);

    // Store tokens and update auth state
    authStore.saveTokens(authData.access_token, authData.refresh_token);
    await authStore.performLogin({
      is_authenticated: true,
      user_id: authData.user.id,
      email: authData.user.email,
    });

    // Redirect to original destination or dashboard
    // Whitelist redirect URLs to prevent open redirect vulnerability
    const allowedRedirects = ['/dashboard', '/inbox', '/archive', '/analytics', '/settings'];
    const requestedRedirect = route.query.redirect as string;
    const redirect = allowedRedirects.includes(requestedRedirect)
      ? requestedRedirect
      : '/dashboard';
    router.push(redirect);
  } catch (err) {
    console.error('OAuth callback error:', err);
    error.value = err instanceof Error ? err.message : 'Login failed';

    // Redirect to login with error after a delay
    setTimeout(() => {
      router.push({ name: 'Login', query: { error: error.value } });
    }, 2000);
  } finally {
    isLoading.value = false;
  }
});
</script>

<template>
  <div class="oauth-callback">
    <div class="callback-container">
      <div class="spinner"></div>
      <h1>Completing login...</h1>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.oauth-callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 24px;
}

.callback-container {
  text-align: center;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 24px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

h1 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

p {
  color: var(--text-secondary);
  font-size: 16px;
}

.error {
  color: #dc2626;
  margin-top: 16px;
}
</style>
