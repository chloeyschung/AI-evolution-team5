# AUTH-002: Social Login - Google

**F-001 Mapping**: Social Login - Google
**Phase**: Phase 1 - MVP (Mobile Focus)
**Priority**: Critical - Primary user onboarding path

## Overview

One-tap Google sign-in. Auto-create account on first login. Rejection of re-registration for deleted accounts within 30 days.

## Requirements

### 1. One-Tap Google Sign-In
- Use Google Sign-In SDK (iOS/Android)
- Single tap to authenticate with Google
- Request minimal scopes: email, profile
- Handle sign-in errors gracefully

### 2. Auto-Create Account on First Login
- If user doesn't exist, create new account automatically
- Extract from Google: email, display name, profile picture
- Generate authentication tokens (AUTH-001)
- Create default user profile and preferences

### 3. Rejection of Re-Registration (30-Day Block)
- Track account deletion timestamp
- If user attempts to re-login within 30 days of deletion: reject
- Error message: "Account recently deleted. Please wait 30 days before re-registering."
- After 30 days: allow new account creation

### 4. Existing User Login
- If user exists with same Google email: login
- Issue new authentication tokens
- Update last login timestamp

## API Design

### POST /api/v1/auth/google

Authenticate with Google and get access tokens.

**Request:**
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

**Response (200 OK - Success):**
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

**Response (403 Forbidden - 30-Day Block):**
```json
{
  "error": "account_restriction",
  "message": "Account recently deleted. Please wait 30 days before re-registering.",
  "available_at": "2024-02-01T00:00:00Z"
}
```

## Data Models

### Updates to UserProfile

Add Google OAuth fields:

```python
class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, nullable=False, index=True)  # NEW
    google_sub = Column(String(100), unique=True, nullable=True, index=True)  # NEW
    display_name = Column(String(100))
    avatar_url = Column(String(500))
    bio = Column(String(500))
    last_login_at = Column(DateTime, nullable=True, index=True)  # NEW
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, index=True)
```

### New: AccountDeletion table

Track deleted accounts for 30-day block:

```python
class AccountDeletion(Base):
    __tablename__ = "account_deletions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    google_sub = Column(String(100), unique=True, nullable=True, index=True)
    deleted_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    block_expires_at = Column(DateTime, nullable=False, index=True)  # deleted_at + 30 days
```

## Flow

### First-Time User

1. User taps "Sign in with Google"
2. Google SDK returns ID token + user info
3. Mobile app calls POST /auth/google
4. Server verifies Google ID token
5. Server checks if email/google_sub exists:
   - **No existing account**: Create new account, issue tokens, return `is_new_user: true`
6. Mobile app shows onboarding (if new user) or INBOX

### Existing User

1. User taps "Sign in with Google"
2. Google SDK returns ID token + user info
3. Mobile app calls POST /auth/google
4. Server verifies Google ID token
5. Server finds existing account by email or google_sub
6. Server issues new tokens, updates last_login_at
7. Mobile app shows INBOX

### Deleted Account (Within 30 Days)

1. User taps "Sign in with Google"
2. Google SDK returns ID token + user info
3. Mobile app calls POST /auth/google
4. Server verifies Google ID token
5. Server checks account_deletions table
6. If block not expired: return 403 with available_at timestamp
7. Mobile app shows error message with countdown

## Security Considerations

1. **Google ID Token Verification**: Verify signature and claims
2. **Email Uniqueness**: Prevent duplicate accounts
3. **30-Day Block Enforcement**: Database check on every login attempt
4. **Token Security**: Use AUTH-001 token system

## Dependencies

- **Depends on**: AUTH-001 (token management)
- **Required by**: AUTH-003, AUTH-004

## Testing

1. First-time login → new account created, tokens issued
2. Existing user login → tokens issued, last_login updated
3. Deleted account (within 30 days) → 403 error
4. Deleted account (after 30 days) → new account created
5. Invalid Google ID token → 401 error
6. Email already exists → login to existing account
