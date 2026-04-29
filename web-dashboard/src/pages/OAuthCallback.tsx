import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';
import { loginWithGoogleCode } from '../api/endpoints';
import styles from './OAuthCallback.module.css';

export default function OAuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const authStore = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = new URLSearchParams(location.search).get('code');
        if (!code) {
          throw new Error('OAuth code missing');
        }

        const authData = await loginWithGoogleCode(code);
        authStore.saveTokens(authData.access_token, authData.refresh_token);
        await authStore.performLogin({
          is_authenticated: true,
          user_id: authData.user.id,
          email: authData.user.email,
        });

        const allowedRedirects = ['/dashboard', '/inbox', '/archive', '/analytics', '/settings'];
        const requestedRedirect = new URLSearchParams(location.search).get('redirect') || '';
        const redirect = allowedRedirects.includes(requestedRedirect) ? requestedRedirect : '/dashboard';
        navigate(redirect);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Login failed';
        setError(errorMessage);
        setTimeout(() => {
          navigate({ pathname: '/login', search: `?error=${encodeURIComponent(errorMessage)}` });
        }, 2000);
      }
    };

    void handleCallback();
  }, [location, navigate, authStore]);

  return (
    <section className={styles.page} data-testid="oauth-callback-page">
      <div className={styles.card}>
        <div className={styles.spinner} aria-hidden="true" />
        <h1>Completing secure login…</h1>
        {error ? <p className={styles.error}>{error}</p> : <p>Please wait while we set up your workspace.</p>}
      </div>
    </section>
  );
}
