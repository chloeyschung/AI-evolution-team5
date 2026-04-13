<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { AppSettings, DEFAULT_SETTINGS, ViewMode } from '../types';

const settings = ref<AppSettings>({ ...DEFAULT_SETTINGS });
const isSaving = ref(false);
const saveMessage = ref<string | null>(null);

onMounted(async () => {
  // Load settings from localStorage
  const saved = localStorage.getItem('briefly_settings');
  if (saved) {
    settings.value = { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
  }
});

const saveSettings = async () => {
  isSaving.value = true;
  saveMessage.value = null;

  try {
    localStorage.setItem('briefly_settings', JSON.stringify(settings.value));
    saveMessage.value = 'Settings saved successfully!';

    // Apply theme
    applyTheme(settings.value.theme);

    setTimeout(() => {
      saveMessage.value = null;
    }, 3000);
  } catch (error) {
    saveMessage.value = 'Failed to save settings';
  } finally {
    isSaving.value = false;
  }
};

const applyTheme = (theme: string) => {
  const root = document.documentElement;
  root.style.setProperty('--theme', theme);
};

const viewModes: { value: ViewMode; label: string }[] = [
  { value: 'grid', label: 'Grid View' },
  { value: 'list', label: 'List View' },
];

const themes: { value: string; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
];
</script>

<template>
  <div class="settings">
    <div class="page-header">
      <h1>Settings</h1>
      <p>Customize your Briefly experience</p>
    </div>

    <div v-if="saveMessage" :class="['message', 'success']">
      {{ saveMessage }}
    </div>

    <div class="settings-card">
      <h2>Appearance</h2>

      <div class="setting-group">
        <label class="setting-label">Theme</label>
        <div class="setting-options">
          <button
            v-for="theme in themes"
            :key="theme.value"
            :class="['option-btn', { active: settings.theme === theme.value }]"
            @click="settings.theme = theme.value as any"
          >
            {{ theme.label }}
          </button>
        </div>
      </div>

      <div class="setting-group">
        <label class="setting-label">Default View</label>
        <div class="setting-options">
          <button
            v-for="view in viewModes"
            :key="view.value"
            :class="['option-btn', { active: settings.defaultView === view.value }]"
            @click="settings.defaultView = view.value"
          >
            {{ view.label }}
          </button>
        </div>
      </div>

      <div class="setting-group">
        <label class="setting-label">Items Per Page</label>
        <input
          v-model.number="settings.itemsPerPage"
          type="number"
          min="10"
          max="100"
          step="10"
          class="number-input"
        />
      </div>
    </div>

    <div class="settings-card">
      <h2>API Configuration</h2>

      <div class="setting-group">
        <label class="setting-label" for="api-url">API Base URL</label>
        <input
          id="api-url"
          v-model="settings.apiBaseUrl"
          type="text"
          placeholder="http://localhost:8000"
          class="text-input"
        />
        <p class="setting-help">
          The URL of your Briefly backend API server.
        </p>
      </div>
    </div>

    <div class="settings-actions">
      <button @click="saveSettings" :disabled="isSaving" class="save-btn">
        {{ isSaving ? 'Saving...' : 'Save Settings' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.settings {
  padding: 24px;
  max-width: 800px;
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

.message {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 14px;
}

.message.success {
  background: #d1fae5;
  color: #047857;
}

.settings-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}

.settings-card h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.setting-group {
  margin-bottom: 24px;
}

.setting-group:last-child {
  margin-bottom: 0;
}

.setting-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.setting-options {
  display: flex;
  gap: 8px;
}

.option-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.option-btn:hover {
  border-color: var(--primary-color);
}

.option-btn.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.number-input,
.text-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
}

.number-input:focus,
.text-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.setting-help {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
}

.save-btn {
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

.save-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
