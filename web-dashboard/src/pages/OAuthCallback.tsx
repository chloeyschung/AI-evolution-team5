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

        // Send code to backend - it handles token exchange with client_secret
        const authData = await loginWithGoogleCode(code);

        // Store tokens and update auth state
        authStore.saveTokens(authData.access_token, authData.refresh_token);
        await authStore.performLogin({
          is_authenticated: true,
          user_id: authData.user.id,
          email: authData.user.email,
        });

        // Redirect to original destination or dashboard
        // Whitelist redirect URLs to prevent open redirect vulnerability
        const allowedRedirects = ['/dashboard', '/inbox', '/archive', '/analytics', '/settings'];
        const requestedRedirect = new URLSearchParams(location.search).get('redirect') || '';
        const redirect = allowedRedirects.includes(requestedRedirect)
          ? requestedRedirect
          : '/dashboard';
        navigate(redirect);
      } catch (err) {
        console.error('OAuth callback error:', err);
        const errorMessage = err instanceof Error ? err.message : 'Login failed';
        setError(errorMessage);

        // Redirect to login with error after a delay
        setTimeout(() => {
          navigate({ pathname: '/login', search: `?error=${encodeURIComponent(errorMessage)}` });
        }, 2000);
      }
    };

    handleCallback();
  }, [location, navigate, authStore]);

  return (
    <div className={styles.oauthCallback}>
      <div className={styles.callbackContainer}>
        <div className={styles.spinner}></div>
        <h1>Completing login...</h1>
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
}
