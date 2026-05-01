# AUTH-006: Google OAuth for Chrome Browser Extension

**Status**: Implemented | **Created**: 2026-05-01 | **Author**: yoonsoo
**F-xxx Mapping**: F-AUTH-006 | **Phase**: Phase 1 - MVP | **Priority**: High

---

## 1. Overview

**Problem**: The Chrome browser extension had no authentication flow. Users could not log in to Briefly from the extension, making save-and-sync features inaccessible without opening the web dashboard separately.

**Solution**: Implement Google OAuth in the extension using `chrome.identity.launchWebAuthFlow` with a `chromiumapp.org` redirect URI, exchanging the auth code via the existing backend `/api/v1/auth/google/code` endpoint.

**Goals**: Allow users to authenticate in the extension popup with their Google account; share the same backend token infrastructure as the web dashboard.

**Non-Goals**: Naver/Kakao login in the extension, persistent cross-device session sync, extension-specific token storage.

---

## 2. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | "Continue with Google" button in extension popup initiates OAuth | P0 |
| FR-2 | OAuth flow runs inside Chrome's native auth window | P0 |
| FR-3 | Auth code is exchanged via backend (client secret never exposed to extension) | P0 |
| FR-4 | On success, extension shows authenticated state with user email | P0 |
| FR-5 | User dismissing the Google window is treated as silent cancellation (no error) | P1 |
| NFR-1 | redirect_uri uses `https://<extension-id>.chromiumapp.org/` pattern | P0 |
| NFR-2 | Web OAuth client ID used (same as backend) so code exchange uses matching credentials | P0 |

---

## 3. User Story / Behavior

As a user, I want to log in to the Briefly extension with my Google account, so that saved pages are synced to my Briefly library.

### Key Behaviors

- Clicking "Continue with Google" opens a Chrome-managed OAuth popup
- Google account selection and consent happen in the popup
- On approval, Chrome intercepts the `chromiumapp.org` redirect and returns the code to the extension
- Extension sends the code + redirect URI to the backend for token exchange
- On success, the popup transitions to the authenticated "READY TO CAPTURE" view

---

## 4. Data Models

### New Tables

None.

### Existing Used

- `user_profiles` (user lookup / creation on first login)
- `user_auth_methods` (Google identity row, via existing `/auth/google/code` flow)

---

## 5. API Design

Uses the existing endpoint:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/google/code` | POST | Exchange Google auth code for Briefly access + refresh tokens |

### Request

```json
{
  "code": "<auth_code_from_google>",
  "redirect_uri": "https://<extension-id>.chromiumapp.org/"
}
```

### Response (200 OK)

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": "...",
  "user": { "id": 1, "email": "user@gmail.com" }
}
```

---

## 6. Implementation

### Files

- `browser-extension/src/popup/popup.ts` — `loginBtn` click handler using `chrome.identity.launchWebAuthFlow`
- `browser-extension/src/shared/auth.ts` — `loginWithGoogleCode(code, redirectUri)` sends to backend
- `browser-extension/.env` — `VITE_GOOGLE_CLIENT_ID` set to Web OAuth client ID

### Key Logic

1. Build auth URL with `client_id`, `redirect_uri=https://<chrome.runtime.id>.chromiumapp.org/`, `response_type=code`, offline scopes
2. Call `chrome.identity.launchWebAuthFlow({ url: authUrl, interactive: true })`
3. Chrome intercepts redirect to `*.chromiumapp.org` and resolves with the full redirect URL
4. Extract `code` from the resolved URL's query params
5. Call `authManager.loginWithGoogleCode(code, redirectUri)` → backend exchanges code for tokens
6. On success, show authenticated popup view

### Google Cloud Console Setup

- **OAuth Client type**: Web application (same client used by backend for code exchange)
- **Authorized redirect URI added**: `https://<extension-id>.chromiumapp.org/`
- **Note**: Each developer loading the extension as unpacked will get a different extension ID and must add their own `chromiumapp.org` URI. When published to Chrome Web Store the ID is fixed.

### Bug Fixed: OAuth Callback Double-Execution

`web-dashboard/src/pages/OAuthCallback.tsx` was calling the token exchange twice on mount due to React StrictMode double-invoking effects. Fixed by changing `useEffect` dependency array from `[location, navigate, authStore]` to `[]` and adding `{ replace: true }` to all `navigate()` calls.

### Dependencies

**Requires** (satisfied by):
- AUTH-002 — existing `/auth/google/code` backend endpoint
- AUTH-005 — `user_auth_methods` identity table for user creation

**Provides** (for future):
- Foundation for adding Naver/Kakao login buttons to the extension popup

---

## 7. Edge Cases

| Scenario | Handling |
|----------|----------|
| User closes Google auth window | `launchWebAuthFlow` throws with 'cancelled'/'closed' message — caught and treated as silent cancellation, no error shown |
| `chrome.runtime.id` unavailable | Would cause auth URL construction to fail; guarded by `if (!clientId)` check |
| Backend exchange fails (wrong credentials) | Error shown in extension popup via `showError()` |
| Stale refresh token in extension storage | Transient refresh error shown in chrome://extensions/ errors panel; does not block new login |
| Different extension ID per developer | Each developer must register their own `chromiumapp.org` URI in Google Cloud Console during development |

---

## 8. Testing

- **Unit**: `chrome.identity.launchWebAuthFlow` mock returning code URL; cancelled flow returns silently
- **Integration**: Full flow from button click → Google popup → code → backend exchange → authenticated state
- **Acceptance**: Extension popup shows user email after Google login; "Save current page" becomes available

---

## 9. Sensory Verification

- **Visual (시각)**: After login, popup header shows "READY TO CAPTURE" and user email in top-right; login screen replaced by save controls
- **Auditory (청각)**: Backend logs show successful `/auth/google/code` call; no console errors in extension popup DevTools
- **Tactile (촉각)**: Google popup opens within ~1s of clicking button; authenticated state appears within ~2s of approving consent

---

## 10. Future Enhancements

1. Add `oauth2` key to `manifest.json` to support `chrome.identity.getAuthToken` flow (eliminates redirect URI registration requirement per developer)
2. Naver/Kakao login buttons in extension popup
3. Single-click re-auth when tokens expire (silent token refresh via `chrome.identity`)

---

## 11. References

- [AUTH-002.md](AUTH-002.md) — Google OAuth backend implementation
- [AUTH-005.md](AUTH-005.md) — Multi-provider identity layer
- [EXT-001.md](EXT-001.md) — Browser extension architecture
- [Chrome Identity API docs](https://developer.chrome.com/docs/extensions/reference/identity/)
