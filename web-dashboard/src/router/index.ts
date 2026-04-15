import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { setAbortController } from '../api/client';

// Global abort controller for request cancellation on navigation
let currentAbortController: AbortController | null = null;

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/inbox',
    name: 'Inbox',
    component: () => import('../views/Inbox.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/archive',
    name: 'Archive',
    component: () => import('../views/Archive.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: () => import('../views/Analytics.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/oauth-callback',
    name: 'OAuthCallback',
    component: () => import('../views/OAuthCallback.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Navigation guard for auth and request cancellation
router.beforeEach(async (to, _from, next) => {
  // Cancel any in-flight requests from previous route
  if (currentAbortController) {
    currentAbortController.abort();
  }
  currentAbortController = new AbortController();
  // Pass the controller to the API client
  setAbortController(currentAbortController);

  const authStore = useAuthStore();

  // Initialize auth if not done (isLoading starts as true, set to false after init)
  if (authStore.$state.isLoading) {
    await authStore.initialize();
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Dashboard' });
  } else {
    next();
  }
});

// Clean up abort controller on route success
router.afterEach(() => {
  // The controller is already aborted in beforeEach, just clear the reference
  currentAbortController = null;
  setAbortController(null);
});

export default router;
