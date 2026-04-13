# AUTH-001: App Entry & Login State

**F-000 Mapping**: App Entry & Login State
**Phase**: Phase 1 - MVP (Mobile Focus)
**Priority**: Critical - Prerequisite for all features

## Overview

Check login state on app launch. If unauthenticated, show login screen immediately. Maintain login state across app restarts with token auto-refresh.

## Requirements

### 1. Login State Check on App Launch
- On app startup, immediately check if user has valid authentication token
- If authenticated: show main INBOX screen
- If unauthenticated: show login screen (AUTH-002)

### 2. Token Management
- Store authentication token securely (mobile keychain/keystore)
- Token includes: access_token, refresh_token, expires_at
- Auto-refresh token before expiration (refresh 5 minutes before expiry)

### 3. Session Validation
- Each API request includes access token in Authorization header
- Server validates token on each request
- If token expired: use refresh token to get new access token
- If refresh failed: force re-login

### 4. Login State Persistence
- Survives app restarts
- Survives app background/foreground transitions
- Survives device reboots (token stored persistently)

## API Design

### GET /api/v1/auth/status
Check current authentication status.

**Request:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "is_authenticated": true,
  "user_id": 1,
  "email": "user@example.com",
  "token_expires_at": "2024-01-01T12:00:00Z"
}
```

**Response (401 Unauthorized):**
```json
{
  "is_authenticated": false,
  "error": "unauthorized"
}
```

### POST /api/v1/auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "<refresh_token>"
}
```

**Response (200 OK):**
```json
{
  "access_token": "<new_access_token>",
  "expires_at": "2024-01-01T13:00:00Z"
}
```

**Response (401 Unauthorized):**
```json
{
  "error": "invalid_refresh_token"
}
```

## Data Models

### AuthenticationToken (new table)
Stores user authentication tokens.

```python
class AuthenticationToken(Base):
    __tablename__ = "authentication_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), unique=True, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)  # For logout/account delete
```

## Security Considerations

1. **Token Storage**: Use mobile secure storage (Keychain/Keystore)
2. **Token Expiry**: Access token valid for 1 hour, refresh token valid for 7 days
3. **Token Rotation**: Issue new refresh token on each refresh
4. **Revocation**: Old tokens invalidated on logout or account delete

## Dependencies

- **Depends on**: None (foundation feature)
- **Required by**: AUTH-002, AUTH-003, AUTH-004, all user-specific features

## Implementation Notes

1. Use JWT (JSON Web Token) for access tokens
2. Use random opaque tokens for refresh tokens
3. Implement token blacklist for revoked tokens
4. Mobile app should handle token refresh transparently

## Testing

1. App launch with valid token → shows INBOX
2. App launch with expired token → auto-refresh → shows INBOX
3. App launch with invalid token → shows login screen
4. App launch with no token → shows login screen
5. Token refresh before expiry → new token issued
6. Token refresh after expiry → force re-login
