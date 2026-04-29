# AUTH-001: App Entry & Login State

**Status**: Implemented | **Created**: 2026-04-14 | **Author**: abraxaspark
**F-xxx Mapping**: F-000 (App Entry & Login State) | **Phase**: Phase 1 - MVP (Mobile Focus) | **Priority**: Critical

---

## 1. Overview

**Problem**: Users need seamless app entry with automatic login state management across app restarts and device reboots.

**Solution**: JWT-based authentication with token auto-refresh, secure storage, and automatic session validation on app launch.

**Goals**: Zero-friction login for returning users, automatic token refresh before expiration, immediate login screen for unauthenticated users

**Non-Goals**: Social login (AUTH-002), multi-device session management, biometric authentication

---

## 2. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Check login state on app launch | P0 |
| FR-2 | Store authentication token securely | P0 |
| FR-3 | Auto-refresh token before expiration | P0 |
| FR-4 | Validate token on each API request | P0 |
| FR-5 | Persist login state across app restarts | P0 |
| FR-6 | Persist login state across device reboots | P0 |
| NFR-1 | Token refresh 5 minutes before expiry | P0 |
| NFR-2 | Access token valid for 1 hour | P0 |
| NFR-3 | Refresh token valid for 7 days | P0 |

---

## 3. User Story / Behavior

As a Briefly user, I want the app to remember my login state, so that I can access my content immediately without re-entering credentials.

### Key Behaviors

- On app startup, immediately check if user has valid authentication token
- If authenticated: show main INBOX screen
- If unauthenticated: show login screen (AUTH-002)
- Auto-refresh token 5 minutes before expiration
- Force re-login if refresh fails

---

## 4. Data Models

### New Tables

**AuthenticationToken**: id, user_id (unique), access_token (hashed), refresh_token, expires_at, created_at, revoked_at

### Existing Used

- `UserProfile` (user information)

---

## 5. API Design

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/status` | GET | Check current authentication status |
| `/api/v1/auth/refresh` | POST | Refresh access token using refresh token |

### Request/Response Examples

**GET /api/v1/auth/status**

Request:
```
Authorization: Bearer <access_token>
```

Response (200 OK - Authenticated):
```json
{
  "is_authenticated": true,
  "user_id": 1,
  "email": "user@example.com",
  "token_expires_at": "2024-01-01T12:00:00Z"
}
```

Response (200 OK - Not Authenticated):
```json
{
  "is_authenticated": false
}
```

**POST /api/v1/auth/refresh**

Request:
```json
{
  "refresh_token": "<refresh_token>"
}
```

Response (200 OK):
```json
{
  "access_token": "<new_access_token>",
  "expires_at": "2024-01-01T13:00:00Z"
}
```

Response (401 Unauthorized):
```json
{
  "error": "invalid_refresh_token"
}
```

---

## 6. Implementation

### Files

- `src/auth/tokens.py` - JWT creation and verification utilities
- `src/data/auth_repository.py` - Token CRUD operations
- `src/data/models.py` - AuthenticationToken model
- `src/api/routes.py` - Auth status and refresh endpoints
- `src/config.py` - JWT configuration (SECRET_KEY, ALGORITHM)

### Key Logic

1. On login, generate JWT access token (1 hour) and opaque refresh token (7 days)
2. Hash access token with SHA-256 before storing in database
3. Send plaintext access token to client only (never store plaintext)
4. Client stores tokens in secure storage (Keychain/Keystore)
5. On each API request, include access token in Authorization header
6. 5 minutes before expiry, auto-refresh using refresh token
7. Token rotation: issue new refresh token on each refresh
8. On logout/delete, set revoked_at timestamp to invalidate tokens

### Dependencies

**Requires** (satisfied by):
- None (foundation feature)

**Provides** (for future):
- AUTH-002, AUTH-003, AUTH-004 - Token management infrastructure
- All user-specific features - Authentication context

---

## 7. Edge Cases

| Scenario | Handling |
|----------|----------|
| No token stored | Show login screen immediately |
| Token expired but refresh valid | Auto-refresh, continue to INBOX |
| Both tokens expired | Force re-login |
| Token revoked (logout/delete) | 401 response, force re-login |
| Invalid token format | 401 response, clear stored token |

---

## 8. Testing

- **Unit**: Token creation, verification, hashing, refresh logic
- **Integration**: Auth status endpoint, refresh endpoint, token rotation
- **Acceptance**: App launch with valid/expired/invalid/no token scenarios

---

## 9. Sensory Verification

- **Visual (시각)**: Authenticated users see INBOX immediately; unauthenticated users see login screen
- **Auditory (청각)**: API logs show token validation results; refresh events logged
- **Tactile (촉각)**: Token refresh completes transparently without user interaction; < 1s latency

---

## 10. Future Enhancements

1. Multi-device session management
2. Biometric authentication (Face ID/Touch ID)
3. Remember me option with extended token validity
4. Session activity logging for security audit

---

## 11. References

- [AUTH-002.md](specs/AUTH-002.md) - Social Login (uses this token system)
- [AUTH-003.md](specs/AUTH-003.md) - Logout (revokes these tokens)
- RFC 8725 - JWT Best Practices
