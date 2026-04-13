<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const isLoading = ref(false);
const error = ref<string | null>(null);

const handleGoogleLogin = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    // Use Chrome Identity API for OAuth
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

    if (!clientId) {
      throw new Error('Google Client ID not configured');
    }

    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${clientId}&` +
      `redirect_uri=${encodeURIComponent(window.location.origin + '/oauth-callback')}&` +
      `response_type=code&` +
      `scope=openid%20email%20profile&` +
      `include_granted_scopes=true&` +
      `access_type=offline&` +
      `prompt=consent`;

    // For now, redirect to Google OAuth
    // In production, use chrome.identity.launchWebAuthFlow
    window.location.href = authUrl;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Login failed';
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <div class="logo">
        <span class="logo-icon">📚</span>
      </div>

      <h1>Briefly</h1>
      <p>Save & summarize web content with AI</p>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <button
        @click="handleGoogleLogin"
        :disabled="isLoading"
        class="google-login-btn"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        {{ isLoading ? 'Signing in...' : 'Continue with Google' }}
      </button>

      <p class="login-note">
        You'll be redirected to Google to sign in, then back to Briefly.
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 24px;
}

.login-container {
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.logo {
  margin-bottom: 24px;
}

.logo-icon {
  font-size: 64px;
}

h1 {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

p {
  color: var(--text-secondary);
  font-size: 16px;
  margin-bottom: 32px;
}

.error-message {
  background: #fef2f2;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 14px;
}

.google-login-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  padding: 14px 24px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: white;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.google-login-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
}

.google-login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-note {
  margin-top: 24px;
  font-size: 13px;
  color: var(--text-tertiary);
}
</style>
