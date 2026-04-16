import { useState } from 'react';
import { Link } from 'react-router-dom';
import styles from './Login.module.css';
import { useAuthStore } from '../stores/useAuthStore';

export default function SignIn() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loginWithEmail = useAuthStore((state) => state.loginWithEmail);

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

  const handleEmailLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const form = e.currentTarget;
    const email = (form.elements.namedItem('email') as HTMLInputElement).value;
    const password = (form.elements.namedItem('password') as HTMLInputElement).value;

    try {
      await loginWithEmail(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed');
      setIsLoading(false);
    }
  };

  return (
    <section className={styles.page} data-testid="login-page">
      <div className={styles.card}>
        <p className={styles.kicker}>Welcome to Briefly</p>
        <h1>Turn "later" into "learned".</h1>
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

        <hr style={{ margin: '1.5rem 0', opacity: 0.2 }} />

        <form onSubmit={handleEmailLogin}>
          <input
            name="email"
            type="email"
            placeholder="Email"
            required
            autoComplete="email"
            className={styles.input}
          />
          <input
            name="password"
            type="password"
            placeholder="Password"
            required
            autoComplete="current-password"
            className={styles.input}
          />
          <button
            type="submit"
            disabled={isLoading}
            className={styles.primaryBtn}
          >
            {isLoading ? 'Signing in…' : 'Sign in with email'}
          </button>
        </form>

        <p style={{ marginTop: '1rem', fontSize: '0.875rem', textAlign: 'center' }}>
          No account? <Link to="/signup">Sign up</Link>
          {' · '}
          <Link to="/forgot-password">Forgot password?</Link>
        </p>
      </div>
    </section>
  );
}
