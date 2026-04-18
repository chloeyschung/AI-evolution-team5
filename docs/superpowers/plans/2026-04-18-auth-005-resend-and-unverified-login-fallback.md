# AUTH-005 Resend + Unverified Login Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이메일 인증 미완료 계정의 교착상태를 해소하기 위해 기존 인증토큰 무효화 + 재발급 + 재발송을 구현하고, 로그인/프론트 UX를 스펙 수준으로 정합화한다.

**Architecture:** 백엔드는 `email_verification_tokens`를 단일 활성 토큰 모델로 운영한다. 미인증 계정의 재가입 또는 명시적 resend 요청이 들어오면 기존 미사용 토큰을 일괄 `used_at` 처리 후 새 토큰을 발급한다. 프론트는 `email_not_verified` 응답을 명시적으로 처리해 재발송 CTA를 제공하고, Axios 인터셉터는 로그인/회원가입 요청의 의도된 401을 세션만료로 오해하지 않도록 제외 경로를 둔다.

**Tech Stack:** FastAPI, SQLAlchemy AsyncSession, Pydantic, React 18, Zustand, Axios, Playwright, pytest

---

## Scope Check

이 작업은 하나의 인증 서브시스템(AUTH-005) 안에서 백엔드 API/프론트 UX/테스트를 함께 수정해야 완결된다. 독립 배포 가능한 별도 서브시스템으로 분리하지 않고 단일 계획으로 진행한다.

---

## File Map

### Backend
- Modify: `src/data/email_auth_repository.py`
  - 인증토큰 무효화/조회 헬퍼 메서드 추가
- Modify: `src/api/schemas.py`
  - resend 요청/응답, login 403 fallback payload 스키마 추가
- Modify: `src/api/routers/auth.py`
  - `register` 재가입 교착해소 로직
  - `POST /auth/verify-email/resend` 추가
  - `login`의 미인증 fallback payload 개선

### Frontend
- Modify: `web-dashboard/src/api/endpoints.ts`
  - resend API 클라이언트 함수 추가
- Modify: `web-dashboard/src/api/client.ts`
  - 401 refresh 인터셉터 auth 엔드포인트 제외
- Modify: `web-dashboard/src/pages/SignIn.tsx`
  - `email_not_verified` 전용 안내 + resend CTA
- Modify: `web-dashboard/src/pages/VerifyEmail.tsx`
  - 만료/실패 페이지에서 이메일 입력 후 resend 가능

### Tests
- Modify: `tests/api/test_auth_email.py`
  - resend/토큰무효화/미인증 로그인 fallback 테스트
- Modify: `tests/data/test_email_auth_repository.py`
  - invalidate verification tokens 테스트
- Modify: `web-dashboard/tests/e2e/auth.spec.ts`
  - 로그인 페이지 resend UX 검증 시나리오 추가
- Delete: `web-dashboard/tests/e2e/test-login.spec.ts`
  - AUTH-005에서 제거된 test-login bypass 테스트 삭제
- Modify: `web-dashboard/playwright.config.ts`
- Modify: `web-dashboard/playwright.integration.config.ts`
  - `VITE_ENABLE_TEST_LOGIN` 제거

### Docs
- Modify: `docs/specs/AUTH-005.md`
  - resend 엔드포인트/동작을 API 및 edge case 표에 명시

---

### Task 1: Repository Token Invalidation Helper

**Files:**
- Modify: `src/data/email_auth_repository.py`
- Test: `tests/data/test_email_auth_repository.py`

- [ ] **Step 1: Write failing repository test for token invalidation**

```python
# tests/data/test_email_auth_repository.py

async def test_invalidate_all_verification_tokens_for_user(user, repo):
    await repo.create_verification_token(user.id, "hash1", utc_now() + timedelta(hours=24))
    await repo.create_verification_token(user.id, "hash2", utc_now() + timedelta(hours=24))

    invalidated = await repo.invalidate_verification_tokens_for_user(user.id)
    assert invalidated == 2

    # Any previously-active token must no longer be consumable
    assert await repo.consume_verification_token("hash1") is None
    assert await repo.consume_verification_token("hash2") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_email_auth_repository.py::test_invalidate_all_verification_tokens_for_user -v`
Expected: FAIL with `AttributeError: 'EmailAuthRepository' object has no attribute 'invalidate_verification_tokens_for_user'`

- [ ] **Step 3: Implement minimal repository method**

```python
# src/data/email_auth_repository.py

    async def invalidate_verification_tokens_for_user(self, user_id: int) -> int:
        """Invalidate all currently active verification tokens for user.

        Marks every unexpired + unused verification token as used.
        Does NOT commit; caller controls transaction boundary.
        """
        result = await self._db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.expires_at > utc_now(),
            )
        )
        tokens = list(result.scalars().all())
        for token in tokens:
            token.used_at = utc_now()
        return len(tokens)
```

- [ ] **Step 4: Run repository test suite**

Run: `uv run pytest tests/data/test_email_auth_repository.py -v`
Expected: PASS (`test_invalidate_all_verification_tokens_for_user` 포함)

- [ ] **Step 5: Commit**

```bash
git add tests/data/test_email_auth_repository.py src/data/email_auth_repository.py
git commit -m "feat(auth): add verification token invalidation helper for resend flow"
```

---

### Task 2: API Schema for Resend + Unverified Login Fallback

**Files:**
- Modify: `src/api/schemas.py`
- Test: `tests/api/test_auth_email.py`

- [ ] **Step 1: Add failing API test asserting unverified login payload fields**

```python
# tests/api/test_auth_email.py

async def test_login_unverified_email_returns_403_with_resend_hint(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_unverified_user(session, email="unverified-hint@example.com", password="Pass1!")

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "unverified-hint@example.com",
        "password": "Pass1!"
    })

    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error"] == "email_not_verified"
    assert detail["can_resend"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/api/test_auth_email.py::test_login_unverified_email_returns_403_with_resend_hint -v`
Expected: FAIL because current payload has only `{"error": "email_not_verified"}`

- [ ] **Step 3: Add schema models for resend and login fallback payload**

```python
# src/api/schemas.py

class ResendVerificationRequest(BaseModel):
    email: str


class ResendVerificationResponse(BaseModel):
    message: str


class EmailNotVerifiedErrorDetail(BaseModel):
    error: str
    can_resend: bool
    message: str
```

- [ ] **Step 4: Run type import check**

Run: `uv run python -c "from src.api.schemas import ResendVerificationRequest, ResendVerificationResponse, EmailNotVerifiedErrorDetail; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add src/api/schemas.py tests/api/test_auth_email.py
git commit -m "feat(auth): add resend and email-not-verified response schemas"
```

---

### Task 3: Register 교착해소 + Resend Endpoint Backend

**Files:**
- Modify: `src/api/routers/auth.py`
- Modify: `src/api/schemas.py` (imports only)
- Test: `tests/api/test_auth_email.py`

- [ ] **Step 1: Write failing API tests for resend endpoint + unverified re-register behavior**

```python
# tests/api/test_auth_email.py

async def test_resend_verification_for_unverified_email_returns_200(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        await make_unverified_user(session, email="resend@example.com", password="Pass1!")

    with patch("src.api.routers.auth.EmailService") as MockEmail:
        MockEmail.return_value.send_verification_email = lambda *a, **kw: None
        resp = await async_client.post("/api/v1/auth/verify-email/resend", json={"email": "resend@example.com"})

    assert resp.status_code == 200
    assert "sent" in resp.json()["message"].lower()


async def test_register_existing_unverified_rotates_token_and_returns_201(async_client, db):
    async with AsyncTestingSessionLocal() as session:
        user, _ = await make_unverified_user(session, email="stuck@example.com", password="Pass1!")
        old_raw = await make_verification_token(session, user.id)

    with patch("src.api.routers.auth.EmailService") as MockEmail:
        MockEmail.return_value.send_verification_email = lambda *a, **kw: None
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "stuck@example.com",
            "password": "AnotherPass2!"
        })

    assert resp.status_code == 201

    # Old token must be invalid after re-registration resend flow
    verify_old = await async_client.get(f"/api/v1/auth/verify-email?token={old_raw}")
    assert verify_old.status_code == 400
```

- [ ] **Step 2: Run only new tests to verify they fail**

Run: `uv run pytest tests/api/test_auth_email.py -k "resend_verification_for_unverified_email_returns_200 or register_existing_unverified_rotates_token_and_returns_201" -v`
Expected: FAIL (route missing / behavior missing)

- [ ] **Step 3: Implement backend logic in router**

```python
# src/api/routers/auth.py (imports)
from ..schemas import (
    # existing imports...
    ResendVerificationRequest,
    ResendVerificationResponse,
)


@router.post("/auth/verify-email/resend")
async def resend_verification_email(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> ResendVerificationResponse:
    email_repo = EmailAuthRepository(db)
    provider_id = hmac_email(request.email)
    method = await email_repo.get_auth_method_by_provider(AuthProvider.EMAIL_PASSWORD, provider_id)

    if method and not method.email_verified:
        await email_repo.invalidate_verification_tokens_for_user(method.user_id)
        raw_token, token_hash = generate_token()
        await email_repo.create_verification_token(
            user_id=method.user_id,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(hours=24),
        )
        try:
            EmailService().send_verification_email(request.email.strip().lower(), raw_token)
        except Exception:
            pass

    # Enumeration-safe response
    return ResendVerificationResponse(
        message="If the account exists and is not verified, a verification email has been sent."
    )


@router.post("/auth/register", status_code=201)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    email_repo = EmailAuthRepository(db)
    normalized_email = request.email.strip().lower()
    provider_id = hmac_email(normalized_email)

    existing = await email_repo.get_auth_method_by_provider(AuthProvider.EMAIL_PASSWORD, provider_id)
    if existing:
        if existing.email_verified:
            raise HTTPException(
                status_code=409,
                detail={"error": "email_exists", "providers": ["email_password"]},
            )

        await email_repo.invalidate_verification_tokens_for_user(existing.user_id)
        raw_token, token_hash = generate_token()
        await email_repo.create_verification_token(
            user_id=existing.user_id,
            token_hash=token_hash,
            expires_at=utc_now() + timedelta(hours=24),
        )
        try:
            EmailService().send_verification_email(normalized_email, raw_token)
        except Exception:
            pass
        return RegisterResponse(message="Verification email sent. Please check your inbox.")

    existing_user = await db.execute(select(UserProfile).where(UserProfile.email == normalized_email))
    existing_user = existing_user.scalar_one_or_none()
    if existing_user:
        user_methods = await email_repo.get_auth_methods_for_user(existing_user.id)
        providers = sorted({m.provider.value for m in user_methods})
        raise HTTPException(status_code=409, detail={"error": "email_exists", "providers": providers})

    user = UserProfile(email=normalized_email, created_at=utc_now(), updated_at=utc_now())
    db.add(user)
    await db.flush()

    await email_repo.create_auth_method(
        user_id=user.id,
        provider=AuthProvider.EMAIL_PASSWORD,
        provider_id=provider_id,
        password_hash=hash_password(request.password),
        email_encrypted=encrypt_email(normalized_email),
    )

    raw_token, token_hash = generate_token()
    await email_repo.create_verification_token(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=utc_now() + timedelta(hours=24),
    )

    try:
        EmailService().send_verification_email(normalized_email, raw_token)
    except Exception:
        pass

    return RegisterResponse(message="Verification email sent. Please check your inbox.")
```

- [ ] **Step 4: Run auth API tests**

Run: `uv run pytest tests/api/test_auth_email.py -v`
Expected: PASS (register/resend/verify/login/password-reset 관련 케이스 통과)

- [ ] **Step 5: Commit**

```bash
git add src/api/routers/auth.py src/api/schemas.py tests/api/test_auth_email.py
git commit -m "feat(auth): add resend verification endpoint and unverified re-register token rotation"
```

---

### Task 4: Login 403 Graceful Fallback Payload

**Files:**
- Modify: `src/api/routers/auth.py`
- Test: `tests/api/test_auth_email.py`

- [ ] **Step 1: Confirm failing expectation for `can_resend` payload**

Run: `uv run pytest tests/api/test_auth_email.py::test_login_unverified_email_returns_403_with_resend_hint -v`
Expected: FAIL if payload not yet extended

- [ ] **Step 2: Implement 403 detail payload enrichment**

```python
# src/api/routers/auth.py

    if not method.email_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "email_not_verified",
                "can_resend": True,
                "message": "Email not verified. Please verify your email or request a new verification email.",
            },
        )
```

- [ ] **Step 3: Re-run single test**

Run: `uv run pytest tests/api/test_auth_email.py::test_login_unverified_email_returns_403_with_resend_hint -v`
Expected: PASS

- [ ] **Step 4: Run full auth API tests**

Run: `uv run pytest tests/api/test_auth_email.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/routers/auth.py tests/api/test_auth_email.py
git commit -m "feat(auth): return resend guidance payload for unverified login attempts"
```

---

### Task 5: Frontend API Client + SignIn Resend UX

**Files:**
- Modify: `web-dashboard/src/api/endpoints.ts`
- Modify: `web-dashboard/src/pages/SignIn.tsx`

- [ ] **Step 1: Add frontend behavior test (component-level expectation in E2E)**

```ts
// web-dashboard/tests/e2e/auth.spec.ts

test('unverified login error shows resend verification CTA', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="email"]', 'unverified@example.com');
  await page.fill('input[name="password"]', 'Pass1!');
  await page.click('button:has-text("Sign in with email")');

  await expect(page.getByText(/email not verified/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /resend verification email/i })).toBeVisible();
});
```

- [ ] **Step 2: Run E2E auth test to verify failure**

Run: `cd web-dashboard && npm run test:e2e -- tests/e2e/auth.spec.ts`
Expected: FAIL because resend button not rendered

- [ ] **Step 3: Implement resend endpoint helper + SignIn error parsing**

```ts
// web-dashboard/src/api/endpoints.ts

export async function resendVerificationEmail(email: string) {
  const client = getApiClient();
  const response = await client.post('/api/v1/auth/verify-email/resend', { email });
  return response.data as { message: string };
}
```

```tsx
// web-dashboard/src/pages/SignIn.tsx (핵심 추가 부분)
import { resendVerificationEmail } from '../api/endpoints';

const [needsVerification, setNeedsVerification] = useState(false);
const [pendingEmail, setPendingEmail] = useState('');
const [notice, setNotice] = useState<string | null>(null);

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

const handleResend = async () => {
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
```

```tsx
// web-dashboard/src/pages/SignIn.tsx (렌더링)
{notice ? <p className={styles.success}>{notice}</p> : null}
{needsVerification ? (
  <button
    type="button"
    className={styles.secondaryBtn}
    onClick={handleResend}
    disabled={isLoading}
  >
    {isLoading ? 'Sending…' : 'Resend verification email'}
  </button>
) : null}
```

- [ ] **Step 4: Run lint + targeted E2E**

Run: `cd web-dashboard && npm run lint && npm run test:e2e -- tests/e2e/auth.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-dashboard/src/api/endpoints.ts web-dashboard/src/pages/SignIn.tsx web-dashboard/tests/e2e/auth.spec.ts
git commit -m "feat(web-auth): show resend CTA on email_not_verified login response"
```

---

### Task 6: VerifyEmail Page에 Resend 직접 제공

**Files:**
- Modify: `web-dashboard/src/pages/VerifyEmail.tsx`
- Modify: `web-dashboard/src/api/endpoints.ts`

- [ ] **Step 1: Add failing E2E assertion for verify-email error recovery UI**

```ts
// web-dashboard/tests/e2e/auth.spec.ts

test('verify-email failure page allows resend by email', async ({ page }) => {
  await page.goto('/verify-email?token=expired-or-invalid-token');
  await expect(page.getByText(/verification failed/i)).toBeVisible();
  await expect(page.locator('input[name="email"]')).toBeVisible();
  await expect(page.getByRole('button', { name: /resend verification email/i })).toBeVisible();
});
```

- [ ] **Step 2: Run targeted test to verify failure**

Run: `cd web-dashboard && npm run test:e2e -- tests/e2e/auth.spec.ts -g "verify-email failure page allows resend by email"`
Expected: FAIL because email input/button not present

- [ ] **Step 3: Implement VerifyEmail resend form**

```tsx
// web-dashboard/src/pages/VerifyEmail.tsx (핵심 추가)
import { verifyEmail, resendVerificationEmail } from '../api/endpoints';

const [resendEmail, setResendEmail] = useState('');
const [resendMessage, setResendMessage] = useState<string | null>(null);
const [isResending, setIsResending] = useState(false);

const handleResend = async (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  setIsResending(true);
  setResendMessage(null);
  try {
    const data = await resendVerificationEmail(resendEmail);
    setResendMessage(data.message);
  } catch (err) {
    setResendMessage(err instanceof Error ? err.message : 'Failed to resend verification email');
  } finally {
    setIsResending(false);
  }
};
```

```tsx
// web-dashboard/src/pages/VerifyEmail.tsx (error branch 렌더링)
{status === 'error' && (
  <>
    <h1>Verification failed</h1>
    <p className={styles.error}>This link is invalid or has expired. Request a new verification email.</p>
    <form onSubmit={handleResend} className={styles.form}>
      <input
        name="email"
        type="email"
        required
        placeholder="Enter your email"
        value={resendEmail}
        onChange={(e) => setResendEmail(e.target.value)}
        className={styles.input}
      />
      <button type="submit" className={styles.primaryBtn} disabled={isResending}>
        {isResending ? 'Sending…' : 'Resend verification email'}
      </button>
    </form>
    {resendMessage ? <p>{resendMessage}</p> : null}
    <Link to="/login" className={styles.primaryBtn} style={{ textAlign: 'center', display: 'block', textDecoration: 'none', lineHeight: '44px' }}>
      Back to sign in
    </Link>
  </>
)}
```

- [ ] **Step 4: Run targeted E2E**

Run: `cd web-dashboard && npm run test:e2e -- tests/e2e/auth.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-dashboard/src/pages/VerifyEmail.tsx web-dashboard/tests/e2e/auth.spec.ts
git commit -m "feat(web-auth): add resend form on verify-email failure state"
```

---

### Task 7: Axios 401 Interceptor 보호 (로그인 요청 제외)

**Files:**
- Modify: `web-dashboard/src/api/client.ts`
- Test: `web-dashboard/tests/e2e/auth.spec.ts`

- [ ] **Step 1: Add failing regression test intent in E2E**

```ts
// web-dashboard/tests/e2e/auth.spec.ts

test('login 401 does not trigger forced redirect loop', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="email"]', 'no-user@example.com');
  await page.fill('input[name="password"]', 'WrongPass1!');
  await page.click('button:has-text("Sign in with email")');

  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText(/invalid credentials|sign in failed/i)).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify current behavior**

Run: `cd web-dashboard && npm run test:e2e -- tests/e2e/auth.spec.ts -g "login 401 does not trigger forced redirect loop"`
Expected: FAIL or flaky if interceptor refresh path interferes

- [ ] **Step 3: Implement auth endpoint skip logic**

```ts
// web-dashboard/src/api/client.ts

function shouldSkip401Refresh(error: AxiosError): boolean {
  const url = error.config?.url ?? '';
  const authNoRefreshPaths = [
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/auth/verify-email',
    '/api/v1/auth/verify-email/resend',
    '/api/v1/auth/password-reset/request',
    '/api/v1/auth/password-reset/confirm',
  ];
  return authNoRefreshPaths.some((path) => url.includes(path));
}

// inside response interceptor
if (error.response?.status !== 401 || shouldSkip401Refresh(error)) {
  return Promise.reject(error);
}
```

- [ ] **Step 4: Run frontend tests**

Run: `cd web-dashboard && npm run test:e2e -- tests/e2e/auth.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-dashboard/src/api/client.ts web-dashboard/tests/e2e/auth.spec.ts
git commit -m "fix(web-auth): skip token refresh flow for intentional auth 401 endpoints"
```

---

### Task 8: Remove Test Login Bypass Residue

**Files:**
- Delete: `web-dashboard/tests/e2e/test-login.spec.ts`
- Modify: `web-dashboard/playwright.config.ts`
- Modify: `web-dashboard/playwright.integration.config.ts`
- Optional Delete if unused: `web-dashboard/src/pages/Login.tsx`

- [ ] **Step 1: Delete obsolete E2E spec**

```bash
rm -f web-dashboard/tests/e2e/test-login.spec.ts
```

- [ ] **Step 2: Remove `VITE_ENABLE_TEST_LOGIN` from playwright webServer commands**

```ts
// web-dashboard/playwright.config.ts
webServer: {
  command: 'npm run dev',
  url: 'http://localhost:3001',
  reuseExistingServer: true,
  timeout: 120000,
},
```

```ts
// web-dashboard/playwright.integration.config.ts
{
  command: 'VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev',
  url: 'http://localhost:3001',
  reuseExistingServer: true,
  timeout: 120000,
}
```

- [ ] **Step 3: Remove dead page component if unreferenced**

Run: `rg -n "pages/Login|from '../pages/Login'|VITE_ENABLE_TEST_LOGIN" web-dashboard/src web-dashboard/tests -S`
Expected: no runtime references.

If only dead file remains:

```bash
rm -f web-dashboard/src/pages/Login.tsx
```

- [ ] **Step 4: Run E2E smoke**

Run: `cd web-dashboard && npm run test:e2e -- tests/e2e/auth.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-dashboard/playwright.config.ts web-dashboard/playwright.integration.config.ts web-dashboard/tests/e2e/auth.spec.ts
git rm web-dashboard/tests/e2e/test-login.spec.ts web-dashboard/src/pages/Login.tsx
# If Login.tsx is kept intentionally, omit from git rm

git commit -m "chore(auth): remove test-login bypass configs and obsolete e2e spec"
```

---

### Task 9: AUTH-005 Spec Sync + Full Verification

**Files:**
- Modify: `docs/specs/AUTH-005.md`

- [ ] **Step 1: Update spec API table and edge cases**

```md
<!-- docs/specs/AUTH-005.md -->
| `/api/v1/auth/verify-email/resend` | POST | None | Reissue verification token and resend email for unverified account |

| Expired verification token | Error page with "resend" option and `/auth/verify-email/resend` recovery |
```

- [ ] **Step 2: Update register/login response examples to current contract**

```json
// 409 Conflict (email already registered)
{ "error": "email_exists", "providers": ["email_password"] }

// 403 Forbidden (not verified)
{ "error": "email_not_verified", "can_resend": true, "message": "Email not verified..." }
```

- [ ] **Step 3: Run backend + frontend verification commands**

Run:

```bash
# backend
uv run pytest tests/data/test_email_auth_repository.py tests/api/test_auth_email.py tests/auth/test_email_auth.py -v

# frontend
cd web-dashboard && npm run lint && npm run test:e2e -- tests/e2e/auth.spec.ts
```

Expected:
- pytest: all PASS
- lint: PASS
- playwright: PASS

- [ ] **Step 4: Sanity-check local DB stuck-account scenario manually**

Run:

```bash
sqlite3 briefly.db ".headers on" ".mode column" "SELECT u.email, m.email_verified, t.used_at, t.expires_at FROM user_profile u JOIN user_auth_methods m ON u.id=m.user_id LEFT JOIN email_verification_tokens t ON t.user_id=u.id WHERE u.email='vetilo4114@dwseal.com' ORDER BY t.created_at DESC LIMIT 5;"
```

Expected:
- resend 이후 직전 토큰 `used_at`가 채워짐
- 최신 토큰 1개만 active 상태

- [ ] **Step 5: Commit**

```bash
git add docs/specs/AUTH-005.md
git commit -m "docs(auth-005): sync resend endpoint and unverified login fallback contract"
```

---

## Self-Review

### 1) Spec Coverage Check
- 교착상태 해소(기존 토큰 무효화 + 재발급 + 재발송): Task 1, Task 3
- 미인증 로그인 graceful fallback: Task 2, Task 4, Task 5
- resend 미구현 보완: Task 3, Task 6
- test login bypass 제거 정합성: Task 8
- spec 문서 동기화: Task 9

Gap 없음.

### 2) Placeholder Scan
- `TBD`, `TODO`, "implement later" 없음
- 각 코드 변경 단계에 실제 코드 블록 포함
- 각 테스트 단계에 실행 커맨드와 기대 결과 포함

### 3) Type/Name Consistency
- Resend API: `POST /api/v1/auth/verify-email/resend`
- 스키마 이름: `ResendVerificationRequest`, `ResendVerificationResponse`
- 에러 키: `email_not_verified`, `can_resend`, `message`
- 프론트 함수명: `resendVerificationEmail`

일관성 확인 완료.

