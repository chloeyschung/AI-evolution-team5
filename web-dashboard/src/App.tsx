import { Outlet, useLocation } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import Header from './components/layout/Header';
import styles from './App.module.css';

const AUTH_PAGES = ['/login', '/oauth-callback'];

function App() {
  const location = useLocation();
  const isAuthPage = AUTH_PAGES.includes(location.pathname);

  const handleError = (error: Error) => {
    console.error('Global error:', error);
  };

  return (
    <ErrorBoundary onError={handleError}>
      <a href="#main-content" className={styles.skipLink}>Skip to content</a>
      {isAuthPage ? (
        <Outlet />
      ) : (
        <div className={styles.shell}>
          <Header />
          <main id="main-content" className={styles.content}>
            <Outlet />
          </main>
        </div>
      )}
    </ErrorBoundary>
  );
}

export default App;
