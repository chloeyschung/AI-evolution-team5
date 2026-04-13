# AUTH-003: Logout

**F-002 Mapping**: Logout
**Phase**: Phase 1 - MVP (Mobile Focus)
**Priority**: High - User session management

## Overview

End current session. Local data retained, syncs on re-login.

## Requirements

### 1. End Current Session
- Revoke current access and refresh tokens
- Server-side token invalidation
- Client receives success confirmation

### 2. Local Data Retention
- All local data (content, swipe history, preferences) remains on device
- Data is NOT deleted on logout
- Data syncs when user re-login with same account

### 3. Re-Login Support
- User can immediately re-login with same credentials
- New tokens issued on re-login
- Local data automatically syncs with server

## API Design

### POST /api/v1/auth/logout

End current session and revoke tokens.

**Request:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

**Response (401 Unauthorized):**
```json
{
  "error": "unauthorized"
}
```

## Implementation Details

### Token Revocation

1. Look up token by access_token in database
2. Set `revoked_at` timestamp on token record
3. Token becomes invalid immediately

### Client-Side Behavior

1. Call POST /auth/logout
2. Clear stored tokens from secure storage
3. Navigate to login screen
4. Local data remains intact

## Dependencies

- **Depends on**: AUTH-001 (token management)
- **Required by**: None

## Testing

1. Logged in user → logout → tokens revoked
2. Revoked token → API request → 401 Unauthorized
3. Logout → re-login → new tokens issued
4. Local data persists across logout/login
