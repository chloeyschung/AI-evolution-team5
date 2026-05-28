"""Reading statistics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...data.database import get_db
from ...data.models import SwipeHistory
from ...api.dependencies import get_current_user
from ...constants import SwipeAction

router = APIRouter()


@router.get("/swipe-stats")
async def get_reading_stats(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return reading statistics for the authenticated user.

    Returns counts of kept, deleted (discarded), and total swipes.
    """
    result = await db.execute(
        select(SwipeHistory.action, func.count(SwipeHistory.id).label("count"))
        .where(SwipeHistory.user_id == user_id)
        .group_by(SwipeHistory.action)
    )
    rows = result.all()

    counts = {row.action: row.count for row in rows}

    kept = counts.get(SwipeAction.KEEP, 0)
    deleted = counts.get(SwipeAction.DISCARD, 0)
    total = kept + deleted

    return {
        "kept": kept,
        "deleted": deleted,
        "skipped": 0,
        "total": total,
    }
