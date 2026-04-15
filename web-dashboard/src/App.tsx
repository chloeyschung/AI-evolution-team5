import { Outlet, useLocation } from 'react-router-dom';
import Header from './components/layout/Header';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  const location = useLocation();

  const showHeader = location.pathname !== '/login' && location.pathname !== '/oauth-callback';

  const handleError = (error: Error) => {
    console.error('Global error:', error);
    // Could send to error tracking service here
  };

  return (
    <ErrorBoundary onError={handleError}>
      <div id="app">
        {showHeader && <Header />}
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;
