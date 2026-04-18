import { useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import AppShell from './components/layout/AppShell';
import styles from './App.module.css';
import { setNavigator } from './utils/navigation';

const AUTH_PAGES = [
  '/login',
  '/signup',
  '/forgot-password',
  '/reset-password',
  '/verify-email',
  '/oauth-callback',
];

function App() {
  const location = useLocation();
  const reactNavigate = useNavigate();
  const isAuthPage = AUTH_PAGES.includes(location.pathname);

  useEffect(() => {
    setNavigator((path, options) => reactNavigate(path, options));
  }, [reactNavigate]);

  const handleError = (error: Error) => {
    console.error('Global error:', error);
  };

  return (
    <ErrorBoundary onError={handleError}>
      <a href="#main-content" className={styles.skipLink}>Skip to content</a>
      {isAuthPage ? <Outlet /> : <AppShell />}
    </ErrorBoundary>
  );
}

export default App;
