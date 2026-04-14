# AUTH-004: Account Delete

**Status**: Implemented | **Created**: 2026-04-14 | **Author**: abraxaspark
**F-xxx Mapping**: F-003 (Account Delete) | **Phase**: Phase 1 - MVP (Mobile Focus) | **Priority**: High

---

## 1. Overview

**Problem**: Users need complete control over their data with the ability to permanently delete their account and all associated data.

**Solution**: Two-step confirmation account deletion with permanent data removal and 30-day re-registration block.

**Goals**: Irreversible deletion with clear warnings, complete data removal (server + client), prevent accidental re-registration

**Non-Goals**: Account deactivation/pause, data export before deletion, grace period for recovery

---

## 2. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Two-step confirmation before deletion | P0 |
| FR-2 | Delete all server-side user data | P0 |
| FR-3 | Prompt client to clear local data | P0 |
| FR-4 | Block re-registration for 30 days | P0 |
| FR-5 | Irreversible action (no undo) | P0 |
| NFR-1 | Cascade delete all related data | P0 |
| NFR-2 | Clear warning messages before confirmation | P0 |

---

## 3. User Story / Behavior

As a Briefly user who no longer wants to use the service, I want to permanently delete my account and all data, so that my information is completely removed and I cannot accidentally re-register.

### Key Behaviors

- User initiates account deletion from settings
- First confirmation: "Are you sure you want to delete your account?"
- Second confirmation: "This action is irreversible. All data will be permanently deleted."
- On final confirmation: all data deleted, 30-day block applied
- Client clears all local data and shows login screen

---

## 4. Data Models

### New Tables

None (uses existing AccountDeletion from AUTH-002)

### Existing Used

- `AccountDeletion` (records deletion for 30-day block)
- `UserProfile` (deleted)
- `AuthenticationToken` (deleted)
- `Content` (all user's content deleted)
- `SwipeHistory` (all user's swipes deleted)
- `UserPreferences` (deleted)
- `InterestTag` (all user's tags deleted)

---

## 5. API Design

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/account/delete` | POST | Permanently delete user account and all data |

### Request/Response Examples

**POST /api/v1/auth/account/delete**

Request:
```
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "confirm": true,
  "confirmation_token": "<confirmation_token_from_step_1>"
}
```

Response (200 OK):
```json
{
  "message": "Account deleted successfully",
  "block_expires_at": "2024-02-01T00:00:00Z"
}
```

Response (400 Bad Request - Missing Confirmation):
```json
{
  "error": "confirmation_required",
  "message": "Two-step confirmation required. Please confirm deletion."
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

- `src/data/auth_repository.py` - Account deletion logic
- `src/data/models.py` - AccountDeletion model (from AUTH-002)
- `src/api/routes.py` - Account delete endpoint

### Key Logic

1. **Deletion Order** (cascade):
   1. Revoke authentication tokens
   2. Record account deletion (30-day block in AccountDeletion table)
   3. Delete user preferences
   4. Delete interest tags
   5. Delete swipe history
   6. Delete content (all user's saved content)
   7. Delete user profile

2. **Two-Step Confirmation Flow**:
   - Step 1: Client sends `{"confirm": true}`, server validates and returns confirmation_token
   - Step 2: Client shows irreversible warning, user confirms
   - Step 3: Client sends confirmation_token, server proceeds with deletion

3. **Client-Side Behavior**:
   - On success: clear all local data, clear tokens, navigate to login screen
   - Show "Account deleted" message with 30-day block notice

### Dependencies

**Requires** (satisfied by):
- AUTH-001 - Token revocation
- AUTH-002 - AccountDeletion table for 30-day block tracking

**Provides** (for future):
- GDPR compliance - Data deletion capability
- Account recovery flow - Check AccountDeletion before allowing re-registration

---

## 7. Edge Cases

| Scenario | Handling |
|----------|----------|
| Invalid/expired token | 401 Unauthorized |
| Missing confirmation | 400 Bad Request with message |
| Invalid confirmation token | 400 Bad Request |
| Concurrent delete requests | Second request fails with 401 (token revoked) |
| Re-login within 30 days | 403 Forbidden (handled by AUTH-002) |
| Re-login after 30 days | Allowed, new account created |

---

## 8. Testing

- **Unit**: Deletion order, cascade delete verification, 30-day block calculation
- **Integration**: Full deletion flow, re-registration block, data verification
- **Acceptance**: Valid deletion, all data removed, 30-day block enforced, after-30-days allowed

---

## 9. Sensory Verification

- **Visual (시각)**: Clear two-step confirmation dialogs, "Account deleted" success message
- **Auditory (청각)**: Deletion events logged, cascade delete completion confirmed
- **Tactile (촉각)**: < 2s deletion completion, immediate navigation to login screen

---

## 10. Future Enhancements

1. Data export before deletion (GDPR right to data portability)
2. Account deactivation/pause option (soft delete)
3. 7-day grace period with recovery option
4. Scheduled deletion (delete after X days)

---

## 11. References

- [AUTH-001.md](specs/AUTH-001.md) - Token revocation on deletion
- [AUTH-002.md](specs/AUTH-002.md) - 30-day block enforcement on re-login
- GDPR Article 17 - Right to erasure
