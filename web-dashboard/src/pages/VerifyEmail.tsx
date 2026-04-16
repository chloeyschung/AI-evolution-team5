import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import styles from './Login.module.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const token = searchParams.get('token') ?? '';

  useEffect(() => {
    if (!token) {
      setStatus('error');
      return;
    }

    fetch(`${API_BASE}/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then((res) => {
        if (res.ok) setStatus('success');
        else setStatus('error');
      })
      .catch(() => setStatus('error'));
  }, [token]);

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
            <Link to="/login" className={styles.primaryBtn} style={{ textAlign: 'center', display: 'block', textDecoration: 'none', lineHeight: '44px' }}>
              Back to sign in
            </Link>
          </>
        )}
      </div>
    </section>
  );
}
