# AUTH-002: Social Login - Google

**Status**: Implemented | **Created**: 2026-04-14 | **Author**: abraxaspark
**F-xxx Mapping**: F-001 (Social Login - Google) | **Phase**: Phase 1 - MVP (Mobile Focus) | **Priority**: Critical

---

## 1. Overview

**Problem**: Users need frictionless onboarding without manual account creation and password management.

**Solution**: One-tap Google sign-in with automatic account creation and 30-day re-registration block for deleted accounts.

**Goals**: Single-tap authentication, zero manual registration steps, prevent immediate re-registration after account deletion

**Non-Goals**: Other OAuth providers (Phase 2), email/password login, SSO for enterprise

---

## 2. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | One-tap Google sign-in using platform SDK | P0 |
| FR-2 | Auto-create account on first login | P0 |
| FR-3 | Block re-registration for 30 days after deletion | P0 |
| FR-4 | Login existing users by email/google_sub | P0 |
| FR-5 | Verify Google ID token signature | P0 |
| NFR-1 | Minimal scopes: email, profile only | P0 |
| NFR-2 | Handle sign-in errors gracefully | P0 |

---

## 3. User Story / Behavior

As a new Briefly user, I want to sign in with my Google account in one tap, so that I can start using the app immediately without creating a password.

### Key Behaviors

- User taps "Sign in with Google" button
- Google SDK presents account selection (if multiple)
- User selects account, Google returns ID token + user info
- Server verifies token, creates account if new, issues auth tokens
- User sees INBOX (existing) or onboarding (new)

---

## 4. Data Models

### New Tables

**AccountDeletion**: id, email (unique), google_sub (unique), deleted_at, block_expires_at

### Existing Used

- `UserProfile` (add: email, google_sub, last_login_at fields)
- `AuthenticationToken` (from AUTH-001)

---

## 5. API Design

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/google` | POST | Authenticate with Google and get access tokens |

### Request/Response Examples

**POST /api/v1/auth/google**

Request:
```json
{
  "google_id_token": "<google_id_token_from_sdk>",
  "google_user_info": {
    "id": "google_user_id",
    "email": "user@gmail.com",
    "name": "User Name",
    "picture": "https://lh3.googleusercontent.com/..."
  }
}
```

Response (200 OK - Success):
```json
{
  "access_token": "<jwt_access_token>",
  "refresh_token": "<opaque_refresh_token>",
  "expires_at": "2024-01-01T13:00:00Z",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "display_name": "User Name",
    "avatar_url": "https://lh3.googleusercontent.com/...",
    "is_new_user": false
  }
}
```

Response (403 Forbidden - 30-Day Block):
```json
{
  "error": "account_restriction",
  "message": "Account recently deleted. Please wait 30 days before re-registering.",
  "available_at": "2024-02-01T00:00:00Z"
}
```

---

## 6. Implementation

### Files

- `src/auth/google_oauth.py` - Google OAuth flow and token verification
- `src/data/models.py` - UserProfile updates, AccountDeletion model
- `src/data/auth_repository.py` - Account creation, deletion tracking
- `src/api/routes.py` - Google login endpoint

### Key Logic

1. **First-Time User**:
   - Verify Google ID token signature and claims
   - Check if email/google_sub exists in UserProfile or AccountDeletion
   - If in AccountDeletion and block not expired: return 403
   - Create new UserProfile with Google data
   - Issue auth tokens (AUTH-001)
   - Return `is_new_user: true`

2. **Existing User**:
   - Verify Google ID token
   - Find existing account by email or google_sub
   - Issue new auth tokens
   - Update last_login_at
   - Return `is_new_user: false`

3. **Deleted Account (Within 30 Days)**:
   - Verify Google ID token
   - Check AccountDeletion table
   - If block_expires_at > now: return 403 with available_at
   - Client shows error with countdown

### Dependencies

**Requires** (satisfied by):
- AUTH-001 - Token management infrastructure

**Provides** (for future):
- AUTH-003, AUTH-004 - User account existence
- DAT-002 - User profile data from Google

---

## 7. Edge Cases

| Scenario | Handling |
|----------|----------|
| Invalid Google ID token | 401 Unauthorized |
| Email already exists | Login to existing account |
| Account deleted within 30 days | 403 with available_at timestamp |
| Account deleted after 30 days | Allow new account creation |
| Google API error | Graceful error message, retry option |

---

## 8. Testing

- **Unit**: Google token verification, account creation logic, 30-day block check
- **Integration**: Full login flow, existing user login, blocked account scenarios
- **Acceptance**: First-time login, existing user, deleted account within/after 30 days

---

## 9. Sensory Verification

- **Visual (시각)**: One-tap Google button, seamless transition to INBOX or onboarding
- **Auditory (청각)**: OAuth flow logs, token verification results, account creation events
- **Tactile (촉각)**: < 2s total login time, immediate INBOX access after authentication

---

## 10. Future Enhancements

1. Additional OAuth providers (Apple, Microsoft)
2. Email verification after Google login
3. Account linking (merge multiple Google accounts)
4. SSO for enterprise/education domains

---

## 11. References

- [AUTH-001.md](specs/AUTH-001.md) - Token management used by this feature
- [AUTH-004.md](specs/AUTH-004.md) - Account deletion (populates AccountDeletion table)
- Google OAuth 2.0 Documentation
