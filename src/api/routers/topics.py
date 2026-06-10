"""Topics router — GET /api/v1/topics (IOS-008)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
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
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicClustersResponse:
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
