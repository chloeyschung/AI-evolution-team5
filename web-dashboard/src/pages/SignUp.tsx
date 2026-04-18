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
          <span className={styles.brandGlyph}>B</span>
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
