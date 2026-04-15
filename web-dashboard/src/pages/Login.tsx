import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './Login.module.css';
import { useAuthStore } from '../stores/useAuthStore';

export default function Login() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const performLogin = useAuthStore((state) => state.performLogin);

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      if (!clientId) {
        throw new Error('Google Client ID not configured');
      }

      const authUrl =
        `https://accounts.google.com/o/oauth2/v2/auth?` +
        `client_id=${clientId}&` +
        `redirect_uri=${encodeURIComponent(window.location.origin + '/oauth-callback')}&` +
        `response_type=code&` +
        `scope=openid%20email%20profile&` +
        `include_granted_scopes=true&` +
        `access_type=offline&` +
        `prompt=consent`;

      window.location.href = authUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      setIsLoading(false);
    }
  };

  const handleTestLogin = () => {
    performLogin({ is_authenticated: true, user_id: 1, email: 'test@localhost' });
    navigate('/dashboard');
  };

  return (
    <section className={styles.page} data-testid="login-page">
      <div className={styles.card}>
        <p className={styles.kicker}>Welcome to Briefly</p>
        <h1>Turn “later” into “learned”.</h1>
        <p className={styles.description}>Log in once, then clear your saved queue in short, focused bursts.</p>

        {error ? <p className={styles.error}>{error}</p> : null}

        <button
          onClick={handleGoogleLogin}
          disabled={isLoading}
          className={styles.primaryBtn}
          aria-label="Continue with Google"
        >
          {isLoading ? 'Signing in…' : 'Continue with Google'}
        </button>

        {import.meta.env.VITE_ENABLE_TEST_LOGIN === 'true' ? (
          <button onClick={handleTestLogin} className={styles.secondaryBtn}>
            Test Login
          </button>
        ) : null}
      </div>
    </section>
  );
}
