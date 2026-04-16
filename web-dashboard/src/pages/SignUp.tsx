import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import styles from './Login.module.css';
import { registerWithEmail } from '../api/endpoints';

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
        setError(err instanceof Error ? err.message : 'Sign up failed');
      }
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <section className={styles.page}>
        <div className={styles.card}>
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
      <div className={styles.card}>
        <p className={styles.kicker}>Create account</p>
        <h1>Join Briefly</h1>

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

        <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', textAlign: 'center' }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </section>
  );
}
