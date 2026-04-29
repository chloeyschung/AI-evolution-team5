import { useEffect, useState, type FormEvent } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import styles from './Login.module.css';
import { resendVerificationEmail, verifyEmail } from '../api/endpoints';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [resendEmail, setResendEmail] = useState('');
  const [resendMessage, setResendMessage] = useState<string | null>(null);
  const [resendError, setResendError] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);
  const token = searchParams.get('token') ?? '';

  useEffect(() => {
    setResendMessage(null);
    setResendError(null);

    if (!token) {
      setStatus('error');
      return;
    }

    verifyEmail(token)
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'));
  }, [token]);

  const handleResend = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsResending(true);
    setResendMessage(null);
    setResendError(null);

    try {
      const data = await resendVerificationEmail(resendEmail);
      setResendMessage(data.message);
    } catch (error) {
      setResendError(error instanceof Error ? error.message : 'Failed to resend verification email');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <section className={styles.page} data-testid="verify-email-page">
      <div className={styles.card}>
        {status === 'loading' && <p>Verifying your email…</p>}
        {status === 'success' && (
          <>
            <h1>Email verified!</h1>
            <p>Your email has been confirmed. You can now sign in.</p>
            <Link
              to="/login"
              className={styles.primaryBtn}
              style={{ textAlign: 'center', display: 'block', textDecoration: 'none', lineHeight: '44px' }}
            >
              Sign in
            </Link>
          </>
        )}
        {status === 'error' && (
          <>
            <h1>Verification failed</h1>
            <p className={styles.error}>This link is invalid or has expired. Please request a new verification email.</p>
            <form onSubmit={handleResend} className={styles.form}>
              <input
                name="email"
                type="email"
                required
                autoComplete="email"
                placeholder="Enter your email"
                value={resendEmail}
                onChange={(event) => setResendEmail(event.target.value)}
                className={styles.input}
              />
              <button type="submit" className={styles.primaryBtn} disabled={isResending}>
                {isResending ? 'Sending…' : 'Resend verification email'}
              </button>
            </form>
            {resendMessage ? <p className={styles.description}>{resendMessage}</p> : null}
            {resendError ? <p className={styles.error}>{resendError}</p> : null}
            <Link to="/login" className={styles.primaryBtn} style={{ textAlign: 'center', display: 'block', textDecoration: 'none', lineHeight: '44px' }}>
              Back to sign in
            </Link>
          </>
        )}
      </div>
    </section>
  );
}
