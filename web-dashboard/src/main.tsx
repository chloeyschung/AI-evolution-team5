import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
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

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
