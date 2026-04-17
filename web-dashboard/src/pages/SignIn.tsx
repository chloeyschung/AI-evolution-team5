import { useState } from 'react';
import { Link } from 'react-router-dom';
import styles from './Login.module.css';
import { useAuthStore } from '../stores/useAuthStore';
import { resendVerificationEmail } from '../api/endpoints';

export default function SignIn() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [pendingEmail, setPendingEmail] = useState('');
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
    setNotice(null);
    setNeedsVerification(false);

    const form = e.currentTarget;
    const email = (form.elements.namedItem('email') as HTMLInputElement).value;
    const password = (form.elements.namedItem('password') as HTMLInputElement).value;

    try {
      await loginWithEmail(email, password);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: { error?: string; message?: string; can_resend?: boolean } } } })
        ?.response?.data?.detail;

      if (detail?.error === 'email_not_verified') {
        setNeedsVerification(Boolean(detail.can_resend));
        setPendingEmail(email);
        setError(detail.message ?? 'Email not verified. Please verify your email.');
      } else {
        setError(err instanceof Error ? err.message : 'Sign in failed');
      }
      setIsLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!pendingEmail) return;
    setIsLoading(true);
    setError(null);
    setNotice(null);
    try {
      const data = await resendVerificationEmail(pendingEmail);
      setNotice(data.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resend verification email');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className={styles.page} data-testid="login-page">
      <div className={styles.card} data-testid="auth-signal-lane">
        <p className={styles.kicker}>Welcome back</p>
        <h1>Briefs become memory.</h1>
        <p className={styles.description}>One login. Steady reading momentum.</p>

        {error ? <p className={styles.error}>{error}</p> : null}
        {notice ? <p className={styles.description}>{notice}</p> : null}

        <button
          onClick={handleGoogleLogin}
          disabled={isLoading}
          className={styles.primaryBtn}
          aria-label="Continue with Google"
        >
          {isLoading ? 'Signing in…' : 'Continue with Google'}
        </button>

        <hr className={styles.divider} />

        <form onSubmit={handleEmailLogin} className={styles.form}>
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
          {needsVerification ? (
            <button
              type="button"
              disabled={isLoading}
              className={styles.secondaryBtn}
              onClick={handleResendVerification}
            >
              {isLoading ? 'Sending…' : 'Resend verification email'}
            </button>
          ) : null}
        </form>

        <p className={styles.metaLinks}>
          New here? <Link to="/signup">Create account</Link>
          {' · '}
          <Link to="/forgot-password">Forgot password?</Link>
        </p>
      </div>
    </section>
  );
}
