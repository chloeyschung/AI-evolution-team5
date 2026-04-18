"""TDD tests asserting account.py and user.py datetime fields use Z-suffix (iOS-compatible).

These tests assert that every datetime field returned by account and user endpoints
ends with "Z", not "+00:00" or bare isoformat. Written BEFORE the fix — should FAIL
initially on the bare .isoformat() calls.

Affected locations:
- account.py line ~181: block_expires_at.isoformat()  (Step 2 of delete — no Z)
- user.py  line ~42-43: profile created_at / updated_at  (GET /profile)
- user.py  line ~67-68: profile created_at / updated_at  (PATCH /profile)
"""

from tests.conftest import AsyncTestingSessionLocal
from tests.factories import make_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

Z_SUFFIX_MSG = "datetime field must end with 'Z' (iOS-compatible UTC suffix)"


def assert_z_suffix(value: str, field: str) -> None:
    assert isinstance(value, str), f"{field}: expected str, got {type(value)}"
    assert value.endswith("Z"), f"{field}: got {value!r} — {Z_SUFFIX_MSG}"


# ---------------------------------------------------------------------------
# 1. POST /auth/account/delete  —  Step 2 block_expires_at (line ~181)
#    Step 1 already has + "Z"; Step 2 (confirmation_token provided) does not.
# ---------------------------------------------------------------------------


async def test_account_delete_step2_block_expires_at_has_z_suffix(async_client, db):
    """block_expires_at in DELETE step-2 response must end with Z."""
    async with AsyncTestingSessionLocal() as session:
        user, access_token = await make_user(session, email="delete-dt@example.com")

    headers = {"Authorization": f"Bearer {access_token}"}

    # Step 1: get the confirmation token
    resp1 = await async_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True},
        headers=headers,
    )
    assert resp1.status_code == 200, f"Step 1 failed: {resp1.json()}"
    step1_data = resp1.json()
    assert_z_suffix(step1_data["block_expires_at"], "step1.block_expires_at")
    confirmation_token = step1_data["confirmation_token"]

    # Step 2: confirm deletion using the token
    resp2 = await async_client.post(
        "/api/v1/auth/account/delete",
        json={"confirm": True, "confirmation_token": confirmation_token},
        headers=headers,
    )
    assert resp2.status_code == 200, f"Step 2 failed: {resp2.json()}"
    step2_data = resp2.json()
    assert_z_suffix(step2_data["block_expires_at"], "step2.block_expires_at")


# ---------------------------------------------------------------------------
# 2. GET /profile  —  created_at / updated_at (lines ~42-43)
# ---------------------------------------------------------------------------


async def test_get_profile_datetime_fields_have_z_suffix(async_client, db):
    """created_at and updated_at in GET /profile must end with Z."""
    async with AsyncTestingSessionLocal() as session:
        _user, access_token = await make_user(session, email="profile-get-dt@example.com")

    resp = await async_client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert_z_suffix(data["created_at"], "profile.created_at")
    assert_z_suffix(data["updated_at"], "profile.updated_at")


# ---------------------------------------------------------------------------
# 3. PATCH /profile  —  created_at / updated_at (lines ~67-68)
# ---------------------------------------------------------------------------


async def test_patch_profile_datetime_fields_have_z_suffix(async_client, db):
    """created_at and updated_at in PATCH /profile must end with Z."""
    async with AsyncTestingSessionLocal() as session:
        _user, access_token = await make_user(session, email="profile-patch-dt@example.com")

    resp = await async_client.patch(
        "/api/v1/profile",
        json={"display_name": "DT Test User"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"
    data = resp.json()
    assert_z_suffix(data["created_at"], "patch_profile.created_at")
    assert_z_suffix(data["updated_at"], "patch_profile.updated_at")
