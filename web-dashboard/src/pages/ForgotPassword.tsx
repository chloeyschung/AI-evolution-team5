import { useState } from 'react';
import { Link } from 'react-router-dom';
import styles from './Login.module.css';
import { requestPasswordReset } from '../api/endpoints';

export default function ForgotPassword() {
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const form = e.currentTarget;
    const email = (form.elements.namedItem('email') as HTMLInputElement).value;

    try {
      await requestPasswordReset(email);
      setSubmitted(true);
    } catch {
      setError('Something went wrong. Please try again.');
      setIsLoading(false);
    }
  };

  if (submitted) {
    return (
      <section className={styles.page}>
        <div className={styles.card} data-testid="auth-signal-lane">
          <h1>Reset link sent</h1>
          <p>If that email is registered, you'll get a reset link shortly.</p>
          <Link to="/login" className={`${styles.primaryBtn} ${styles.primaryLink}`}>
            Back to sign in
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.page} data-testid="forgot-password-page">
      <div className={styles.card} data-testid="auth-signal-lane">
        <p className={styles.kicker}>Reset access</p>
        <h1>Reset and return.</h1>
        <p className={styles.description}>Use the email on your account and we'll send a reset link.</p>

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
          <button type="submit" disabled={isLoading} className={styles.primaryBtn}>
            {isLoading ? 'Sending…' : 'Send reset link'}
          </button>
        </form>

        <p className={styles.metaLinks}>
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </section>
  );
}
