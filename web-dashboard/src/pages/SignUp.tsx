import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import styles from './Login.module.css';
import { registerWithEmail } from '../api/endpoints';

function resolveSignUpError(err: unknown): string {
  const message = err instanceof Error ? err.message : 'Sign up failed';
  const maybeAxios = err as { response?: unknown; code?: string; message?: string };
  const hasNoHttpResponse = typeof maybeAxios === 'object' && maybeAxios !== null && !maybeAxios.response;
  const networkLike = hasNoHttpResponse && (maybeAxios.code === 'ERR_NETWORK' || message.includes('Network Error'));

  if (networkLike) {
    return 'Cannot reach API server. Check backend is running and set VITE_API_BASE_URL to /api for local proxy.';
  }

  return message;
}

export default function SignUp() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const form = e.currentTarget;
    const email = (form.elements.namedItem('email') as HTMLInputElement).value;
    const password = (form.elements.namedItem('password') as HTMLInputElement).value;
    const confirm = (form.elements.namedItem('confirm') as HTMLInputElement).value;

    if (password !== confirm) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }

    try {
      const data = await registerWithEmail(email, password);
      setSuccess(data.message);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: { error?: string } } } })
        ?.response?.data?.detail;
      if (detail?.error === 'email_exists') {
        setError('That email is already registered. Try signing in.');
      } else {
        setError(resolveSignUpError(err));
      }
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <section className={styles.page}>
        <div className={styles.card} data-testid="auth-signal-lane">
          <h1>Check your inbox</h1>
          <p>{success}</p>
          <button onClick={() => navigate('/login')} className={styles.primaryBtn}>
            Go to sign in
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.page} data-testid="signup-page">
      <div className={styles.card} data-testid="auth-signal-lane">
        <div className={styles.brandRow} aria-hidden="true">
          <svg className={styles.brandGlyph} viewBox="0 0 32 32" aria-hidden="true">
            <rect x="1" y="1" width="30" height="30" rx="9" fill="var(--color-signal)" />
            <path d="M9 10.5 C 9 9.67 9.67 9 10.5 9 H 17.2 C 20.4 9 22.6 10.8 22.6 13.6 C 22.6 15.2 21.7 16.4 20.4 17 C 22.1 17.6 23.2 19 23.2 20.9 C 23.2 23.9 20.8 26 17.2 26 H 10.5 C 9.67 26 9 25.33 9 24.5 Z M 13 12.5 V 16 H 16.5 C 17.8 16 18.6 15.3 18.6 14.25 C 18.6 13.2 17.8 12.5 16.5 12.5 Z M 13 19 V 22.5 H 17 C 18.4 22.5 19.2 21.75 19.2 20.75 C 19.2 19.75 18.4 19 17 19 Z" fill="var(--color-signal-on)" />
          </svg>
          <p className={styles.brandCaption}>Read in briefs. Remember longer.</p>
        </div>
        <p className={styles.kicker}>Create account</p>
        <h1>Build your reading ritual.</h1>
        <p className={styles.description}>Save what matters, then come back to it with less friction.</p>

        {error ? <p className={styles.error}>{error}</p> : null}

        <form onSubmit={handleSubmit} className={styles.form}>
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
            autoComplete="new-password"
            minLength={8}
            className={styles.input}
          />
          <input
            name="confirm"
            type="password"
            placeholder="Confirm password"
            required
            autoComplete="new-password"
            className={styles.input}
          />
          <button type="submit" disabled={isLoading} className={styles.primaryBtn}>
            {isLoading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className={styles.metaLinks}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </section>
  );
}
