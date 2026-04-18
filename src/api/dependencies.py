"""Shared FastAPI dependency functions used across domain routers."""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants import ErrorCode
from ..data.auth_repository import AuthenticationRepository
from ..data.database import get_db


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    Authorization: str | None = Header(None),
) -> int:
    """Get current user ID from Bearer token.

    Args:
        db: Database session
        Authorization: Authorization header with Bearer token

    Returns:
        User ID

    Raises:
        401: Invalid or missing token
    """
    from src.auth.tokens import verify_access_token

    if not Authorization or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail=ErrorCode.UNAUTHORIZED)

    token = Authorization[7:]  # Remove "Bearer " prefix

    # First verify JWT signature
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail=ErrorCode.UNAUTHORIZED)

    # Then verify token exists in database (rotation check)
    auth_repo = AuthenticationRepository(db)
    token_record = await auth_repo.get_token_by_access_token(token)

    if not token_record:
        raise HTTPException(status_code=401, detail=ErrorCode.UNAUTHORIZED)

    return token_record.user_id
