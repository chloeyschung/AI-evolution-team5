import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import styles from './Login.module.css';
import { useAuthStore } from '../stores/useAuthStore';
import { resendVerificationEmail } from '../api/endpoints';

type AuthStep = 'email' | 'password';

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" focusable="false">
      <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
      <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
      <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z"/>
    </svg>
  );
}

export default function SignIn() {
  const navigate = useNavigate();
  const [step, setStep] = useState<AuthStep>('email');
  const [emailValue, setEmailValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);
  const loginWithEmail = useAuthStore((state) => state.loginWithEmail);

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      if (!clientId) throw new Error('Google Client ID not configured');
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

  const handleEmailContinue = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const email = (e.currentTarget.elements.namedItem('email') as HTMLInputElement).value;
    setEmailValue(email);
    setError(null);
    setStep('password');
  };

  const handlePasswordSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setNotice(null);
    setNeedsVerification(false);
    const password = (e.currentTarget.elements.namedItem('password') as HTMLInputElement).value;
    try {
      await loginWithEmail(emailValue, password);
      setIsLoading(false);
      navigate('/dashboard', { replace: true });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: { error?: string; message?: string; can_resend?: boolean } } } })
        ?.response?.data?.detail;
      if (detail?.error === 'email_not_verified') {
        setNeedsVerification(Boolean(detail.can_resend));
        setError(detail.message ?? 'Email not verified. Please verify your email.');
      } else {
        setError(err instanceof Error ? err.message : 'Sign in failed');
      }
      setIsLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setIsLoading(true);
    setError(null);
    setNotice(null);
    try {
      const data = await resendVerificationEmail(emailValue);
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
        <p className={styles.kicker}>Briefly</p>
        <h1>Log in or create an account.</h1>

        {error ? <p className={styles.error}>{error}</p> : null}
        {notice ? <p className={styles.description}>{notice}</p> : null}

        {step === 'email' ? (
          <div className={styles.stepPane}>
            <form onSubmit={handleEmailContinue} className={styles.form}>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel} htmlFor="sign-in-email">
                  Email Address
                </label>
                <input
                  id="sign-in-email"
                  name="email"
                  type="email"
                  defaultValue={emailValue}
                  required
                  autoComplete="email"
                  autoFocus
                  className={styles.input}
                />
              </div>
              <button type="submit" className={styles.primaryBtn}>
                Continue
              </button>
            </form>

            <div className={styles.dividerRow}>
              <span className={styles.dividerLine} aria-hidden="true" />
              <span className={styles.dividerLabel}>or</span>
              <span className={styles.dividerLine} aria-hidden="true" />
            </div>

            <p className={styles.legalText}>
              By continuing, you agree to our{' '}
              <Link to="/terms">Terms of Service</Link>
              {' '}and{' '}
              <Link to="/privacy">Privacy Policy</Link>.
            </p>

            <button
              onClick={handleGoogleLogin}
              disabled={isLoading}
              className={styles.oauthBtn}
              aria-label="Continue with Google"
            >
              <GoogleIcon />
              Continue with Google
            </button>

            <p className={styles.metaLinks}>
              New here? <Link to="/signup">Create account</Link>
            </p>
          </div>
        ) : (
          <div className={styles.stepPane}>
            <div className={styles.emailChip}>
              <span className={styles.emailChipText}>{emailValue}</span>
              <button
                type="button"
                className={styles.editEmailBtn}
                onClick={() => { setStep('email'); setError(null); setNotice(null); }}
              >
                Edit
              </button>
            </div>

            <form onSubmit={handlePasswordSubmit} className={styles.form}>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel} htmlFor="sign-in-password">
                  Password
                </label>
                <input
                  id="sign-in-password"
                  name="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  autoFocus
                  className={styles.input}
                />
              </div>
              <button type="submit" disabled={isLoading} className={styles.primaryBtn}>
                {isLoading ? 'Signing in…' : 'Sign in'}
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
              <Link to="/forgot-password">Forgot password?</Link>
              {' · '}
              New here? <Link to="/signup">Create account</Link>
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
