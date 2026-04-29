# AUTH-003: Logout

**Status**: Implemented | **Created**: 2026-04-14 | **Author**: abraxaspark
**F-xxx Mapping**: F-002 (Logout) | **Phase**: Phase 1 - MVP (Mobile Focus) | **Priority**: High

---

## 1. Overview

**Problem**: Users need to end their session securely while preserving local data for potential re-sync on re-login.

**Solution**: Server-side token revocation with client-side token clearance, preserving all local data for sync on re-login.

**Goals**: Immediate session termination, data preservation for re-sync, seamless re-login support

**Non-Goals**: Data deletion (AUTH-004), multi-device logout, logout all devices feature

---

## 2. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Revoke current access and refresh tokens | P0 |
| FR-2 | Server-side token invalidation | P0 |
| FR-3 | Retain all local data on device | P0 |
| FR-4 | Support immediate re-login | P0 |
| FR-5 | Auto-sync local data on re-login | P0 |
| NFR-1 | Token invalidation is immediate | P0 |
| NFR-2 | Local data survives app restart | P0 |

---

## 3. User Story / Behavior

As a Briefly user sharing a device, I want to logout securely, so that the next user cannot access my content but my data is preserved for when I login again.

### Key Behaviors

- User initiates logout from settings
- Server revokes current tokens (sets revoked_at)
- Client clears stored tokens from secure storage
- Client navigates to login screen
- All local data (content, swipes, preferences) remains intact
- Re-login restores sync with server

---

## 4. Data Models

### New Tables

None (uses existing AuthenticationToken from AUTH-001)

### Existing Used

- `AuthenticationToken` (revoked_at field set on logout)

---

## 5. API Design

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/logout` | POST | End current session and revoke tokens |

### Request/Response Examples

**POST /api/v1/auth/logout**

Request:
```
Authorization: Bearer <access_token>
```

Response (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

Response (401 Unauthorized):
```json
{
  "error": "unauthorized"
}
```

---

## 6. Implementation

### Files

- `src/data/auth_repository.py` - Token revocation logic
- `src/api/routes.py` - Logout endpoint

### Key Logic

1. **Token Revocation**:
   - Look up token by access_token in database
   - Set revoked_at timestamp on token record
   - Token becomes invalid immediately

2. **Client-Side Behavior**:
   - Call POST /auth/logout
   - On success: clear stored tokens from secure storage
   - Navigate to login screen
   - Local data remains intact (no deletion)

3. **Re-Login**:
   - User logs in again (AUTH-002)
   - New tokens issued
   - Local data automatically syncs with server

### Dependencies

**Requires** (satisfied by):
- AUTH-001 - Token management and revocation infrastructure

**Provides** (for future):
- Multi-device session management - Token revocation pattern

---

## 7. Edge Cases

| Scenario | Handling |
|----------|----------|
| Already logged out | 401 Unauthorized (idempotent) |
| Token expired before logout | 401 Unauthorized, client clears local tokens |
| Network error during logout | Retry or force clear local tokens on next app launch |
| Concurrent requests after logout | All rejected with 401 |

---

## 8. Testing

- **Unit**: Token revocation sets revoked_at correctly
- **Integration**: Logout endpoint, token invalidation, re-login flow
- **Acceptance**: Logout → tokens revoked → API with old token returns 401 → re-login works

---

## 9. Sensory Verification

- **Visual (시각)**: Immediate navigation to login screen after logout
- **Auditory (청각)**: Logout event logged, token revocation confirmed in server logs
- **Tactile (촉각)**: < 500ms logout completion, immediate login screen display

---

## 10. Future Enhancements

1. "Logout all devices" button
2. Session activity list with individual revoke options
3. Graceful logout on token expiry (auto-logout vs prompt)
4. Logout confirmation dialog (prevent accidental logout)

---

## 11. References

- [AUTH-001.md](specs/AUTH-001.md) - Token system being revoked
- [AUTH-002.md](specs/AUTH-002.md) - Re-login flow after logout
