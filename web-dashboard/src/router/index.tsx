import { createBrowserRouter, Navigate } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';

// Protected route component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
      }}>
        Loading...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// Lazy load page components
const Dashboard = lazyLoad(() => import('../pages/Dashboard'));
const Inbox = lazyLoad(() => import('../pages/Inbox'));
const Archive = lazyLoad(() => import('../pages/Archive'));
const Analytics = lazyLoad(() => import('../pages/Analytics'));
const Settings = lazyLoad(() => import('../pages/Settings'));
const Login = lazyLoad(() => import('../pages/Login'));
const OAuthCallback = lazyLoad(() => import('../pages/OAuthCallback'));

// Helper for lazy loading with error boundary
function lazyLoad(importFn: () => Promise<{ default: React.ComponentType }>) {
  let Module: React.ComponentType | null = null;
  let promise: Promise<void> | null = null;

  function LoadComponent() {
    if (Module) return <Module />;

    if (!promise) {
      promise = importFn().then((mod) => {
        Module = mod.default;
        promise = null;
      });
    }

    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
      }}>
        Loading...
      </div>
    );
  }

  return LoadComponent;
}

// Set up abort controller on route changes
let currentAbortController: AbortController | null = null;

const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    ),
  },
  {
    path: '/inbox',
    element: (
      <ProtectedRoute>
        <Inbox />
      </ProtectedRoute>
    ),
  },
  {
    path: '/archive',
    element: (
      <ProtectedRoute>
        <Archive />
      </ProtectedRoute>
    ),
  },
  {
    path: '/analytics',
    element: (
      <ProtectedRoute>
        <Analytics />
      </ProtectedRoute>
    ),
  },
  {
    path: '/settings',
    element: (
      <ProtectedRoute>
        <Settings />
      </ProtectedRoute>
    ),
  },
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/oauth-callback',
    element: <OAuthCallback />,
  },
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
], {
  basename: '/',
});

export { router, ProtectedRoute };
