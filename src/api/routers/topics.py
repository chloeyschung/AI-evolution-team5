"""Topics router — GET /api/v1/topics (IOS-008).

On first call with no existing clusters, triggers background clustering so the
next pull-to-refresh shows dynamic topic sections.
POST /api/v1/topics/refresh — demo mode: force re-clustering synchronously.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...data.database import get_db
from ...data.models import UserTopicCluster
from ..dependencies import get_current_user

router = APIRouter(prefix="/topics", tags=["topics"])


class TopicClusterResponse(BaseModel):
    id: int
    title_ko: str
    keywords_en: list[str]
    content_ids: list[int]


class TopicClustersResponse(BaseModel):
    clusters: list[TopicClusterResponse]


@router.get("", response_model=TopicClustersResponse)
async def get_topic_clusters(
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicClustersResponse:
    result = await db.execute(
        select(UserTopicCluster)
        .where(UserTopicCluster.user_id == user_id)
        .order_by(UserTopicCluster.generated_at.desc())
    )
    clusters = result.scalars().all()

    if not clusters:
        # First call with no clusters — schedule background generation.
        # Response returns [] immediately; next refresh will show clusters.
        from ...ai.topic_clusterer import cluster_and_save_for_user
        background_tasks.add_task(cluster_and_save_for_user, user_id)

    return TopicClustersResponse(
        clusters=[
            TopicClusterResponse(
                id=c.id,
                title_ko=c.title_ko,
                keywords_en=c.keywords_en or [],
                content_ids=c.content_ids or [],
            )
            for c in clusters
        ]
    )


@router.post("/refresh", response_model=TopicClustersResponse)
async def refresh_topic_clusters(
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicClustersResponse:
    """Demo mode: trigger re-clustering in background and return current clusters immediately.

    Unlike GET /topics (triggers only when empty), this always schedules
    a new clustering run. iOS receives the current clusters instantly and
    shuffles them; the next Refresh call will show the newly generated clusters.
    """
    from ...ai.topic_clusterer import cluster_and_save_for_user

    background_tasks.add_task(cluster_and_save_for_user, user_id)

    result = await db.execute(
        select(UserTopicCluster)
        .where(UserTopicCluster.user_id == user_id)
        .order_by(UserTopicCluster.generated_at.desc())
    )
    clusters = result.scalars().all()

    return TopicClustersResponse(
        clusters=[
            TopicClusterResponse(
                id=c.id,
                title_ko=c.title_ko,
                keywords_en=c.keywords_en or [],
                content_ids=c.content_ids or [],
            )
            for c in clusters
        ]
    )
