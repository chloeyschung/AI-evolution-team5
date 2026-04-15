import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './styles/main.css';

// Apply theme on mount
function applyTheme() {
  const settings = localStorage.getItem('briefly_settings');
  let theme = 'system';

  if (settings) {
    try {
      theme = JSON.parse(settings).theme || 'system';
    } catch {
      // Invalid settings, use default
    }
  }

  const root = document.documentElement;
  if (theme === 'system') {
    root.setAttribute('data-theme', 'system');
  } else {
    root.setAttribute('data-theme', theme);
  }
}

applyTheme();

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);
app.mount('#app');
