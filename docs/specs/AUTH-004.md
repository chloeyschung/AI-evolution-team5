# AUTH-004: Account Delete

**F-003 Mapping**: Account Delete
**Phase**: Phase 1 - MVP (Mobile Focus)
**Priority**: High - User data control

## Overview

Permanent deletion of account and all data. 2-step confirmation. 30-day re-registration block. Full server + local data deletion.

## Requirements

### 1. 2-Step Confirmation
- First confirmation: "Are you sure you want to delete your account?"
- Second confirmation: "This action is irreversible. All data will be permanently deleted."
- Both confirmations required before deletion proceeds

### 2. Permanent Data Deletion
- **Server-side**: All user data deleted from database
  - User profile
  - Authentication tokens
  - All content (saved URLs, summaries)
  - Swipe history
  - User preferences
  - Interest tags
- **Client-side**: App prompts user to clear local data

### 3. 30-Day Re-Registration Block
- Deleted account cannot be re-registered for 30 days
- Same email or Google account blocked
- Block tracked in `account_deletions` table
- After 30 days: new account can be created

### 4. Irreversible Action
- No undo or recovery option
- Data permanently deleted (no soft delete)
- Clear warning before confirmation

## API Design

### POST /api/v1/auth/account/delete

Permanently delete user account and all data.

**Request:**
```
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "confirm": true,
  "confirmation_token": "<confirmation_token_from_step_1>"
}
```

**Response (200 OK):**
```json
{
  "message": "Account deleted successfully",
  "block_expires_at": "2024-02-01T00:00:00Z"
}
```

**Response (400 Bad Request - Missing Confirmation):**
```json
{
  "error": "confirmation_required",
  "message": "Two-step confirmation required. Please confirm deletion."
}
```

**Response (401 Unauthorized):**
```json
{
  "error": "unauthorized"
}
```

## Implementation Details

### Deletion Order

1. Revoke authentication tokens
2. Record account deletion (30-day block)
3. Delete user preferences
4. Delete interest tags
5. Delete swipe history
6. Delete content
7. Delete user profile

### 2-Step Confirmation Flow

**Step 1: Request Confirmation Token**
- Client calls POST /auth/account/delete with `{"confirm": true}`
- Server validates token, returns confirmation token
- Client shows second confirmation dialog

**Step 2: Confirm Deletion**
- Client calls POST /auth/account/delete with confirmation token
- Server validates confirmation token
- Server proceeds with deletion

### Client-Side Behavior

1. User initiates account deletion
2. Show first confirmation dialog
3. If confirmed, show second confirmation (irreversible warning)
4. If confirmed, call API
5. On success:
   - Clear all local data
   - Clear stored tokens
   - Navigate to login screen
   - Show "Account deleted" message

## Data Models

Uses existing `AccountDeletion` table (created in AUTH-002):

```python
class AccountDeletion(Base):
    __tablename__ = "account_deletions"

    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, nullable=False)
    google_sub = Column(String(100), unique=True, nullable=True)
    deleted_at = Column(DateTime, nullable=False)
    block_expires_at = Column(DateTime, nullable=False)  # deleted_at + 30 days
```

## Dependencies

- **Depends on**: AUTH-001 (token management), AUTH-002 (account deletion tracking)
- **Required by**: None

## Security Considerations

1. Valid authentication token required
2. Two-step confirmation prevents accidental deletion
3. 30-day block prevents immediate re-registration
4. All data permanently deleted (no recovery)

## Testing

1. Valid token + confirmation → account deleted
2. Invalid token → 401 Unauthorized
3. Missing confirmation → 400 Bad Request
4. Deleted account → re-login within 30 days → 403 Forbidden
5. Deleted account → re-login after 30 days → new account created
6. All user data deleted from database
