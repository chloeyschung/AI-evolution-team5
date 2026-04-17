# AUTH-005: Email/Password Authentication & Multi-Provider Identity Layer

**Status**: Design | **Created**: 2026-04-16 | **Author**: abraxaspark
**F-xxx Mapping**: TBD | **Phase**: Phase 1 - MVP | **Priority**: High

---

## 1. Overview

**Problem**: Briefly currently supports Google OAuth only. Users who prefer email/password login are excluded, and the architecture has no provider-agnostic identity layer — adding Kakao, Naver, GitHub etc. would require duplicating per-provider code indefinitely.

**Solution**: Introduce a `user_auth_methods` identity table (the standard "identities" pattern) as the backbone for all auth providers. Layer email/password sign-up/sign-in on top as the first non-OAuth method. Refactor Google OAuth to use **Authlib** as the provider transport layer so future providers require only a config entry.

**Goals**:
- Email/password registration with verified accounts
- Email/password sign-in coexisting with Google OAuth
- Explicit account linking when same email exists across providers
- Passwords hashed with Argon2id; login emails encrypted at rest with Fernet
- Extensible to Kakao, Naver, GitHub with minimal per-provider work
- Forgot-password reset flow via email
- Remove dev-only test login bypass (`VITE_ENABLE_TEST_LOGIN`)

**Non-Goals**: Rate limiting (follow-up feature), multi-device session management, biometric auth, social profile import from OAuth providers

---

## 2. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | User can register with email + password | P0 |
| FR-2 | Registration sends verification email; account inactive until verified | P0 |
| FR-3 | User can sign in with email + password after verification | P0 |
| FR-4 | User can request a password reset link via email | P0 |
| FR-5 | Password reset link is single-use and expires in 1 hour | P0 |
| FR-6 | Google OAuth login continues to work unchanged | P0 |
| FR-7 | Same-email conflict across providers returns 409 with explicit linking prompt | P0 |
| FR-8 | User can link accounts after authenticating both identities | P1 |
| FR-9 | Test login bypass removed from frontend and `.env` | P0 |
| NFR-1 | Passwords stored as Argon2id hash (time=3, mem=65536, par=4) | P0 |
| NFR-2 | Login email stored Fernet-encrypted in `user_auth_methods` | P0 |
| NFR-3 | Verification and reset tokens stored as SHA-256 hash only | P0 |
| NFR-4 | Forgot-password response is identical whether email exists or not | P0 |
| NFR-5 | Authlib used as OAuth2 transport for all provider flows | P1 |

---

## 3. User Story / Behavior

### Sign-up
1. User visits `/auth/signup`, enters email + password
2. Backend creates unverified `user_auth_methods` row; sends verification email
3. User clicks link → `GET /api/v1/auth/verify-email?token=...` → account activated
4. User redirected to sign-in page with success message

### Sign-in (email/password)
1. User visits `/auth/login`, enters email + password
2. Backend computes `HMAC-SHA256(email, LOOKUP_KEY)`, looks up matching `user_auth_methods` row, verifies Argon2id hash
3. On success: issues access + refresh tokens (same as Google OAuth path)
4. On 409 (email exists under different provider): frontend shows linking prompt

### Account Linking
1. User signs in with Google; backend detects same email exists under `email_password`
2. Returns `HTTP 409 {"conflict": "email_exists", "providers": ["email_password"]}`
3. Frontend: "An account with this email exists. Sign in with email/password to link accounts."
4. User authenticates with email/password → `POST /api/v1/auth/link-account` with both tokens
5. Backend verifies both identities → adds second `user_auth_methods` row on same `user_id`

### Forgot Password
1. User visits `/auth/forgot-password`, submits email
2. Backend always responds: *"If that email exists, a reset link was sent"* (no enumeration)
3. User clicks reset link → enters new password → `POST /api/v1/auth/password-reset/confirm`
4. Token marked used; user redirected to sign-in

---

## 4. Data Models

### New Table: `user_auth_methods`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | FK → `user_profiles.id` CASCADE DELETE | |
| `provider` | ENUM(`google`, `email_password`, `kakao`, `naver`, `github`) | |
| `provider_id` | TEXT NOT NULL | `google_sub` for OAuth; `HMAC-SHA256(normalized_email, LOOKUP_KEY)` for `email_password` — deterministic, safe to index |
| `password_hash` | TEXT NULL | Argon2id hash; NULL for OAuth rows |
| `email_encrypted` | TEXT NULL | Fernet-encrypted email for `email_password`; NULL for OAuth rows (display/recovery use only) |
| `email_verified` | BOOLEAN DEFAULT FALSE | |
| `verified_at` | DATETIME NULL | |
| `created_at` | DATETIME DEFAULT NOW | |
| `updated_at` | DATETIME DEFAULT NOW | |
| UNIQUE | `(provider, provider_id)` | |

### New Table: `email_verification_tokens`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | FK → `user_profiles.id` | |
| `token_hash` | TEXT UNIQUE | SHA-256 of raw token sent in email |
| `expires_at` | DATETIME | 24h TTL |
| `used_at` | DATETIME NULL | Set on consumption; single-use enforced |
| `created_at` | DATETIME | |

### New Table: `password_reset_tokens`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | FK → `user_profiles.id` | |
| `token_hash` | TEXT UNIQUE | SHA-256 of raw token sent in email |
| `expires_at` | DATETIME | 1h TTL |
| `used_at` | DATETIME NULL | Single-use enforced |
| `created_at` | DATETIME | |

### Migration: `user_profiles`
- `google_sub` column → **dropped**; data migrated to `user_auth_methods` row (`provider='google'`, `provider_id=google_sub`)

---

## 5. API Design

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/register` | POST | None | Create account, send verification email |
| `/api/v1/auth/verify-email` | GET | None | Consume `?token=` link from email |
| `/api/v1/auth/login` | POST | None | Email+password → access+refresh tokens |
| `/api/v1/auth/password-reset/request` | POST | None | Send reset link to email |
| `/api/v1/auth/password-reset/confirm` | POST | None | Consume token + set new password |
| `/api/v1/auth/link-account` | POST | Bearer | Link two authenticated identities |

### Request/Response Examples

**POST /api/v1/auth/register**
```json
// Request
{ "email": "user@example.com", "password": "..." }

// 201 Created
{ "message": "Verification email sent" }

// 409 Conflict (email already registered)
{ "error": "email_exists", "providers": ["google"] }
```

**POST /api/v1/auth/login**
```json
// Request
{ "email": "user@example.com", "password": "..." }

// 200 OK
{ "access_token": "...", "refresh_token": "...", "expires_at": "..." }

// 401 Unauthorized
{ "error": "invalid_credentials" }

// 403 Forbidden (not verified)
{ "error": "email_not_verified" }
```

**POST /api/v1/auth/password-reset/request**
```json
// Request
{ "email": "user@example.com" }

// 200 OK (always, regardless of whether email exists)
{ "message": "If that email exists, a reset link was sent" }
```

---

## 6. Implementation

### New Files

| File | Purpose |
|------|---------|
| `src/auth/email_auth.py` | `hash_password`, `verify_password`, `encrypt_email`, `decrypt_email`, `generate_token` |
| `src/auth/authlib_providers.py` | Authlib OAuth2 config per provider; Google refactored to use this |
| `src/data/email_auth_repository.py` | CRUD for `user_auth_methods`, `email_verification_tokens`, `password_reset_tokens` |
| `src/services/email_service.py` | SMTP wrapper; sends verification + reset email templates |
| `scripts/seed_dev_user.py` | Dev script: creates pre-verified test account without email step |
| `tests/factories.py` | `make_user()`, `make_unverified_user()`, `make_reset_token()` — bypass SMTP in tests |

### Modified Files

| File | Change |
|------|--------|
| `src/data/models.py` | Add `UserAuthMethod`, `EmailVerificationToken`, `PasswordResetToken` models; drop `UserProfile.google_sub` |
| `src/api/routes.py` | Add 6 new endpoints; refactor Google routes to use Authlib |
| `src/auth/google_oauth.py` | Refactor HTTP calls to delegate to Authlib |
| `web-dashboard/src/pages/Login.tsx` | Remove test login button and `handleTestLogin()`; rename → `SignIn.tsx` |
| `web-dashboard/.env` | Remove `VITE_ENABLE_TEST_LOGIN` |
| `web-dashboard/src/stores/useAuthStore.ts` | Add `loginWithEmail()`, `pendingLinkConflict` state |

### New Frontend Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/auth/signup` | `SignUp.tsx` | Registration form |
| `/auth/login` | `SignIn.tsx` | Sign-in (replaces `Login.tsx`) |
| `/auth/forgot-password` | `ForgotPassword.tsx` | Request reset link |
| `/auth/reset-password` | `ResetPassword.tsx` | Consume token + new password |
| `/auth/verify-email` | `VerifyEmail.tsx` | Consume verification token on mount |

### New Dependencies

| Package | Purpose | Add via |
|---------|---------|---------|
| `argon2-cffi` | Argon2id password hashing | `uv add argon2-cffi` |
| `authlib` | OAuth2 provider abstraction | `uv add authlib` |

(`cryptography` for Fernet already present; `smtplib` is stdlib)

### Environment Variables (`.env` additions)

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
EMAIL_FROM=noreply@briefly.app
APP_BASE_URL=http://localhost:5173
EMAIL_LOOKUP_KEY=<32-byte hex key for HMAC-SHA256 email lookup>
```

---

## 7. Security Model

| Concern | Mechanism |
|---------|-----------|
| Password storage | Argon2id, `time=3 mem=65536 par=4` (OWASP minimum for interactive login) |
| Email lookup index | `HMAC-SHA256(normalized_email, EMAIL_LOOKUP_KEY)` — deterministic, keyed, safe to index; resists rainbow tables |
| Email at rest | Fernet symmetric encryption using `FIELD_ENCRYPTION_KEY` (existing key) — for display/recovery |
| Token storage (verify/reset) | SHA-256 hash only; raw token sent once via email, never persisted |
| Token entropy | `secrets.token_urlsafe(32)` = 256 bits |
| Token reuse | `used_at` set on first consumption; second use rejected |
| Email enumeration | Forgot-password always returns identical 200 response |
| Account linking | Requires re-authentication of both identities before merge |
| Test bypass | `VITE_ENABLE_TEST_LOGIN` removed; no dev-mode bypass routes in backend |

---

## 8. Dev/Test Ergonomics

### `scripts/seed_dev_user.py`
```bash
uv run python scripts/seed_dev_user.py
# Creates: test@localhost / testpass123 — pre-verified, no email step
```

### `tests/factories.py`
```python
make_user(email="x@test.com")     # verified auth method, no SMTP
make_unverified_user()             # for testing verification flow
make_reset_token(user)             # returns (raw_token, db_record)
```

### `tests/conftest.py` fixture
```python
@pytest.fixture
def auth_client(client, db):
    user = make_user()
    token = issue_access_token(user)
    client.headers["Authorization"] = f"Bearer {token}"
    return client, user
```
Tests require zero SMTP config and zero manual DB inspection.

---

## 9. Edge Cases

| Scenario | Handling |
|----------|----------|
| Register with already-verified email | 409 with `providers` list (no info leak) |
| Login before email verification | 403 `email_not_verified` |
| Expired verification token | Error page with "resend" option |
| Expired reset token | 400 `token_expired`; user re-requests |
| Link account — one token invalid | 401; restart linking flow |
| `google_sub` migration — NULL google_sub rows | Skip migration row, log warning |

---

## 10. Testing

- **Unit**: `hash_password`, `verify_password`, `encrypt_email`/`decrypt_email`, `generate_token`, token TTL checks
- **Integration**: All 6 new endpoints; Google OAuth unchanged; account linking; migration
- **Acceptance**:
  - Register → verify → login → access protected route
  - Forgot password → reset → login with new password
  - Google login + same email → 409 → link → both methods work
- **Factories** used for all tests; SMTP never called in test suite

---

## 11. Sensory Verification

- **Visual (시각)**: SignUp, SignIn, ForgotPassword, ResetPassword, VerifyEmail pages render correctly; no test login button present
- **Auditory (청각)**: SMTP sends verification/reset emails (check inbox in manual test); server logs show Argon2id timing
- **Tactile (촉각)**: Login with email/password < 500ms; registration response < 300ms

---

## 12. Future Enhancements

1. Rate limiting on `/auth/login` and `/auth/password-reset/request`
2. Add Kakao, Naver, GitHub as providers via `authlib_providers.py` (config only)
3. "Connected accounts" settings page showing all linked providers
4. Password strength meter on sign-up form

---

## 13. References

- [AUTH-001.md](AUTH-001.md) — Token infrastructure reused unchanged
- [AUTH-002.md](AUTH-002.md) — Google OAuth being refactored (not replaced)
- [ARCH-002](../decisions/ARCH-002-hybrid-jwt-session-with-hashed-encrypted-tokens.md) — JWT + Fernet architecture this extends
- [ARCH-006](../decisions/ARCH-006-security-in-depth-perimeter-for-external-io.md) — Security-in-depth patterns
- [ARCH-014](../decisions/ARCH-014-multi-provider-identity-table-and-email-auth.md) — Identity table architecture implemented by this spec
- OWASP Password Storage Cheat Sheet — Argon2id parameters
