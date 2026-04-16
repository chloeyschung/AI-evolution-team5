import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import App from '../App';
import { useAuthStore } from '../stores/useAuthStore';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isLoading = useAuthStore((state) => state.isLoading);

  if (isLoading) {
    return <div style={{ minHeight: '50vh', display: 'grid', placeItems: 'center' }}>Loading…</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

const Dashboard = lazyLoad(() => import('../pages/Dashboard'));
const Inbox = lazyLoad(() => import('../pages/Inbox'));
const Archive = lazyLoad(() => import('../pages/Archive'));
const Analytics = lazyLoad(() => import('../pages/Analytics'));
const Settings = lazyLoad(() => import('../pages/Settings'));
const SignIn = lazyLoad(() => import('../pages/SignIn'));
const SignUp = lazyLoad(() => import('../pages/SignUp'));
const ForgotPassword = lazyLoad(() => import('../pages/ForgotPassword'));
const ResetPassword = lazyLoad(() => import('../pages/ResetPassword'));
const VerifyEmail = lazyLoad(() => import('../pages/VerifyEmail'));
const OAuthCallback = lazyLoad(() => import('../pages/OAuthCallback'));

function lazyLoad(importFn: () => Promise<{ default: React.ComponentType }>) {
  let Module: React.ComponentType | null = null;
  let loadingPromise: Promise<void> | null = null;
  let loadError: unknown | null = null;

  function LoadComponent() {
    const [loaded, setLoaded] = React.useState(false);

    if (!loadingPromise) {
      loadingPromise = importFn()
        .then((mod) => {
          Module = mod.default;
          setLoaded(true);
        })
        .catch((err) => {
          loadError = err;
          setLoaded(true);
        })
        .finally(() => {
          loadingPromise = null;
        });
    }

    if (loadError) {
      console.error('Failed to load component:', loadError);
      return <div style={{ minHeight: '50vh', display: 'grid', placeItems: 'center', color: '#c0392b' }}>Failed to load component</div>;
    }

    if (loaded && Module) {
      return <Module />;
    }

    return <div style={{ minHeight: '50vh', display: 'grid', placeItems: 'center' }}>Loading…</div>;
  }

  return React.memo(LoadComponent);
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'inbox',
        element: (
          <ProtectedRoute>
            <Inbox />
          </ProtectedRoute>
        ),
      },
      {
        path: 'archive',
        element: (
          <ProtectedRoute>
            <Archive />
          </ProtectedRoute>
        ),
      },
      {
        path: 'analytics',
        element: (
          <ProtectedRoute>
            <Analytics />
          </ProtectedRoute>
        ),
      },
      {
        path: 'settings',
        element: (
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        ),
      },
      {
        path: 'login',
        element: <SignIn />,
      },
      {
        path: 'signup',
        element: <SignUp />,
      },
      {
        path: 'forgot-password',
        element: <ForgotPassword />,
      },
      {
        path: 'reset-password',
        element: <ResetPassword />,
      },
      {
        path: 'verify-email',
        element: <VerifyEmail />,
      },
      {
        path: 'oauth-callback',
        element: <OAuthCallback />,
      },
      {
        path: '*',
        element: <Navigate to="/dashboard" replace />,
      },
    ],
  },
], {
  basename: '/',
});

export { router, ProtectedRoute };
