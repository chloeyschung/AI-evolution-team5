import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import styles from './Login.module.css';
import { confirmPasswordReset } from '../api/endpoints';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const form = e.currentTarget;
    const newPassword = (form.elements.namedItem('password') as HTMLInputElement).value;
    const confirm = (form.elements.namedItem('confirm') as HTMLInputElement).value;

    if (newPassword !== confirm) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }

    try {
      await confirmPasswordReset(token, newPassword);
      navigate('/login', { state: { message: 'Password updated. You can now sign in.' } });
    } catch {
      setError('Invalid or expired reset link. Please request a new one.');
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <section className={styles.page}>
        <div className={styles.card}>
          <p className={styles.error}>Invalid reset link. Please request a new one.</p>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.page} data-testid="reset-password-page">
      <div className={styles.card}>
        <p className={styles.kicker}>Reset password</p>
        <h1>Set new password</h1>

        {error ? <p className={styles.error}>{error}</p> : null}

        <form onSubmit={handleSubmit} className={styles.form}>
          <input
            name="password"
            type="password"
            placeholder="New password"
            required
            autoComplete="new-password"
            minLength={8}
            className={styles.input}
          />
          <input
            name="confirm"
            type="password"
            placeholder="Confirm new password"
            required
            autoComplete="new-password"
            className={styles.input}
          />
          <button type="submit" disabled={isLoading} className={styles.primaryBtn}>
            {isLoading ? 'Updating…' : 'Update password'}
          </button>
        </form>
      </div>
    </section>
  );
}
