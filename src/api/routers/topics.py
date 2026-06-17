"""Topics router — GET /api/v1/topics (IOS-008).

On first call with no existing clusters, triggers background clustering so the
next pull-to-refresh shows dynamic topic sections.
POST /api/v1/topics/refresh — demo mode: force re-clustering synchronously.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...data.database import get_db
from ...data.models import UserTopicCluster
from ...middleware.rate_limiter import limiter
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
@limiter.limit("20/minute")
async def refresh_topic_clusters(
    request: Request,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicClustersResponse:
    """Demo mode: run re-clustering synchronously and return freshly generated clusters.

    Waits for clustering to complete so iOS receives new clusters immediately
    on the same request. Skips if clustering is already in progress.
    """
    from ...ai.topic_clusterer import cluster_and_save_for_user

    await cluster_and_save_for_user(user_id)

    # Commit (or rollback) to end the current transaction snapshot so the
    # re-query sees clusters committed by cluster_and_save_for_user's own session.
    await db.commit()

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
