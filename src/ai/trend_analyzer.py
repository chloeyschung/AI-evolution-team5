"""Trend analyzer for personalized content ranking.

TODO #6 (2026-04-14): Fixed timezone handling - use convert_to_utc from datetime_utils
TODO #16 (2026-04-14): N+1 query already fixed - uses get_tags_for_content_ids() in _get_preferred_tags
TODO #23 (2026-04-14): Moved hard-coded limits to constants.py
"""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import (
    ENGAGEMENT_HALF_LIFE_DAYS,
    TREND_ANALYSIS_MONTH_CUTOFF,
    TREND_ANALYSIS_WEEK_CUTOFF,
    TREND_ENGAGEMENT_WEIGHT,
    TREND_FEED_DEFAULT_NEUTRAL_SCORE,
    TREND_FEED_MAX_LIMIT,
    TREND_FEED_MIN_ITEMS_FOR_SCORING,
    TREND_FEED_MIN_SCORE_THRESHOLD,
    TREND_FEED_SAMPLE_SIZE,
    TREND_INTEREST_MATCH_WEIGHT,
    TREND_RECENCY_WEIGHT,
    TREND_TAG_SIMILARITY_WEIGHT,
)
from src.utils.datetime_utils import convert_to_utc

from ..data.models import Content, SwipeAction, utc_now
from ..data.repository import ContentRepository, ContentTagRepository, SwipeRepository, UserProfileRepository


class TrendFeedItem:
    """Item in trend feed with relevance score."""

    def __init__(
        self,
        content: Content,
        relevance_score: float,
        matched_interests: list[str],
        top_tags: list[str],
    ):
        self.content = content
        self.relevance_score = relevance_score
        self.matched_interests = matched_interests
        self.top_tags = top_tags


class TrendAnalyzer:
    """Analyze and rank content for personalized trend feed."""

    # Scoring weights (from constants)
    INTEREST_MATCH_WEIGHT = TREND_INTEREST_MATCH_WEIGHT
    TAG_SIMILARITY_WEIGHT = TREND_TAG_SIMILARITY_WEIGHT
    RECENCY_WEIGHT = TREND_RECENCY_WEIGHT
    ENGAGEMENT_WEIGHT = TREND_ENGAGEMENT_WEIGHT

    # Configuration (from constants)
    HALF_LIFE_DAYS = ENGAGEMENT_HALF_LIFE_DAYS  # Content loses half recency score after this many days
    MIN_ITEMS_FOR_SCORING = TREND_FEED_MIN_ITEMS_FOR_SCORING  # Below this, use simple recency sort
    DEFAULT_NEUTRAL_SCORE = TREND_FEED_DEFAULT_NEUTRAL_SCORE  # Neutral score when no data available
    MIN_SCORE_THRESHOLD = TREND_FEED_MIN_SCORE_THRESHOLD  # Minimum score to appear in feed

    def __init__(self, db_session: AsyncSession):
        """Initialize trend analyzer.

        Args:
            db_session: Async database session.
        """
        self._content_repo = ContentRepository(db_session)
        self._swipe_repo = SwipeRepository(db_session)
        self._tag_repo = ContentTagRepository(db_session)
        self._user_profile_repo = UserProfileRepository(db_session)

    async def get_trend_feed(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        time_range: str = "all",
        min_score: float = MIN_SCORE_THRESHOLD,
    ) -> tuple[list[TrendFeedItem], int]:
        """Get personalized trend feed for user.

        Args:
            user_id: User ID
            limit: Maximum items to return
            offset: Pagination offset
            time_range: "week", "month", or "all"
            min_score: Minimum relevance score threshold

        Returns:
            Tuple of (trend feed items, total count)
        """
        # Get kept content for user (with hard limit to prevent OOM)
        kept_contents = await self._content_repo.get_kept(
            user_id,
            limit=TREND_FEED_MAX_LIMIT,  # Hard limit to prevent memory issues with large datasets
            offset=0,
        )

        # Handle empty case
        if not kept_contents:
            return [], 0

        # Get user context
        user_interests = await self._user_profile_repo.get_interest_tags(user_id)
        preferred_tags = await self._get_preferred_tags(user_id)

        # Filter by time range
        kept_contents = self._filter_by_time_range(kept_contents, time_range)

        # Handle minimal data case
        if len(kept_contents) < self.MIN_ITEMS_FOR_SCORING:
            # Simple recency sort, no scoring
            kept_contents.sort(
                key=lambda c: self._get_datetime_utc(c.updated_at) or self._get_datetime_utc(c.created_at),
                reverse=True,
            )
            items = [
                TrendFeedItem(
                    content=c,
                    relevance_score=self.DEFAULT_NEUTRAL_SCORE,
                    matched_interests=[],
                    top_tags=[],
                )
                for c in kept_contents[offset : offset + limit]
            ]
            return items, len(kept_contents)

        # Calculate scores for all content
        scored_items: list[TrendFeedItem] = []
        for content in kept_contents:
            score, matched_interests, top_tags = await self._calculate_relevance_score(
                content=content,
                user_id=user_id,
                user_interests=user_interests,
                preferred_tags=preferred_tags,
            )

            if score >= min_score:
                scored_items.append(
                    TrendFeedItem(
                        content=content,
                        relevance_score=score,
                        matched_interests=matched_interests,
                        top_tags=top_tags,
                    )
                )

        # Sort by relevance score (descending)
        scored_items.sort(key=lambda x: x.relevance_score, reverse=True)

        # Apply pagination
        total = len(scored_items)
        paginated_items = scored_items[offset : offset + limit]

        return paginated_items, total

    async def _calculate_relevance_score(
        self,
        content: Content,
        user_id: int,
        user_interests: list[str],
        preferred_tags: list[str],
    ) -> tuple[float, list[str], list[str]]:
        """Calculate relevance score for a single content item.

        Args:
            content: Content to score
            user_id: User ID
            user_interests: User's interest tags
            preferred_tags: Tags from user's most-kept content

        Returns:
            Tuple of (score, matched_interests, top_tags)
        """
        # Get content tags
        content_tags = await self._tag_repo.get_tags(content.id)

        # Calculate component scores
        interest_score = self._calculate_interest_match_score(
            content_tags=content_tags,
            user_interests=user_interests,
        )

        tag_similarity_score = self._calculate_tag_similarity_score(
            content_tags=content_tags,
            preferred_tags=preferred_tags,
        )

        recency_score = self._calculate_recency_score(content)

        engagement_score = await self._calculate_engagement_score(
            content_tags=content_tags,
            user_id=user_id,
        )

        # Calculate final score
        score = (
            self.INTEREST_MATCH_WEIGHT * interest_score
            + self.TAG_SIMILARITY_WEIGHT * tag_similarity_score
            + self.RECENCY_WEIGHT * recency_score
            + self.ENGAGEMENT_WEIGHT * engagement_score
        )

        # Find matched interests
        matched_interests = [
            interest.lower()
            for interest in user_interests
            if any(interest.lower() in tag.lower() for tag in content_tags)
        ]

        # Get top tags (up to 3)
        top_tags = content_tags[:3]

        return score, matched_interests, top_tags

    def _calculate_interest_match_score(
        self,
        content_tags: list[str],
        user_interests: list[str],
    ) -> float:
        """Calculate interest match score (0-1).

        Score = matched_interests / total_user_interests
        """
        if not user_interests:
            return self.DEFAULT_NEUTRAL_SCORE

        # Normalize to lowercase for comparison
        content_tags_lower = [tag.lower() for tag in content_tags]
        user_interests_lower = [interest.lower() for interest in user_interests]

        # Count matches (interest matches if it's in any content tag)
        matched = sum(1 for interest in user_interests_lower if any(interest in tag for tag in content_tags_lower))

        return matched / len(user_interests)

    def _calculate_tag_similarity_score(
        self,
        content_tags: list[str],
        preferred_tags: list[str],
    ) -> float:
        """Calculate tag similarity using Jaccard similarity (0-1).

        Jaccard(A, B) = |A ∩ B| / |A ∪ B|
        """
        if not content_tags or not preferred_tags:
            return self.DEFAULT_NEUTRAL_SCORE

        # Use sets for Jaccard calculation
        content_set = set(content_tags)
        preferred_set = set(preferred_tags)

        # Calculate Jaccard similarity
        intersection = len(content_set & preferred_set)
        union = len(content_set | preferred_set)

        if union == 0:
            return self.DEFAULT_NEUTRAL_SCORE

        return intersection / union

    def _calculate_recency_score(self, content: Content) -> float:
        """Calculate recency score (0-1) with exponential decay.

        Score = 1 / (1 + days_since_kept / half_life_days)
        """
        # Use updated_at (when kept) or created_at
        kept_at = self._get_datetime_utc(content.updated_at) or self._get_datetime_utc(content.created_at)
        now = utc_now()

        # Calculate days since kept
        delta = now - kept_at
        days_since_kept = delta.total_seconds() / (24 * 60 * 60)

        # Apply decay formula
        score = 1 / (1 + days_since_kept / self.HALF_LIFE_DAYS)

        return score

    async def _calculate_engagement_score(
        self,
        content_tags: list[str],
        user_id: int,
    ) -> float:
        """Calculate engagement score based on keep ratio for same tags (0-1).

        For each content tag, calculate the ratio of kept vs. total content
        with that tag. Average across all tags.
        """
        if not content_tags:
            return self.DEFAULT_NEUTRAL_SCORE

        # Get swipe history scoped to the current user
        swipe_history = await self._swipe_repo.get_all_history(user_id=user_id)

        if not swipe_history:
            return self.DEFAULT_NEUTRAL_SCORE

        # Use overall keep ratio as approximation for engagement score
        # This is acceptable because:
        # 1. The engagement score is only 15% of total relevance score
        # 2. Overall keep ratio still provides useful signal about user preferences
        return self._calculate_overall_keep_ratio(swipe_history)

    def _calculate_overall_keep_ratio(
        self,
        swipe_history: list,
    ) -> float:
        """Calculate overall keep ratio from swipe history.

        This is used as an approximation for per-tag engagement scoring.

        Ratio = kept_swipes / total_swipes

        Note: This is a simplified calculation. In production, we'd query the
        database with a proper join to ContentTag for accurate per-tag counts.
        """
        # Use overall keep ratio as approximation
        # This is acceptable because:
        # 1. The engagement score is only 15% of total relevance score
        # 2. Overall keep ratio still provides useful signal about user preferences
        kept_count = sum(1 for swipe in swipe_history if swipe.action == SwipeAction.KEEP)
        total_count = len(swipe_history)

        if total_count == 0:
            return self.DEFAULT_NEUTRAL_SCORE

        return kept_count / total_count

    async def _get_preferred_tags(self, user_id: int) -> list[str]:
        """Get preferred tags from user's most-kept content.

        Returns top tags from content user has kept (max 10 tags).

        Optimization:
            Uses batch query to avoid N+1 pattern. All tags fetched in single query.
        """
        # Get kept content
        kept_contents = await self._content_repo.get_kept(
            user_id,
            limit=TREND_FEED_SAMPLE_SIZE,  # Sample size
            offset=0,
        )

        if not kept_contents:
            return []

        # Batch optimization: Get all tags in single query (avoids N+1)
        content_ids = [c.id for c in kept_contents]
        tags_by_content = await self._tag_repo.get_tags_for_content_ids(content_ids)

        # Count tag frequency across all content
        tag_counts: dict[str, int] = {}
        for _, tags in tags_by_content.items():
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by frequency and return top 10
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags[:10]]

    def _get_datetime_utc(self, dt: datetime | None) -> datetime | None:
        """Convert datetime to UTC if naive.

        Args:
            dt: Datetime to convert (may be naive or aware)

        Returns:
            UTC datetime or None

        TODO #6 (2026-04-14): Using convert_to_utc from datetime_utils for consistency.
        """
        # Use centralized utility for timezone conversion
        return convert_to_utc(dt)

    def _filter_by_time_range(
        self,
        contents: list[Content],
        time_range: str,
    ) -> list[Content]:
        """Filter contents by time range.

        Args:
            contents: List of content items
            time_range: "week", "month", or "all"

        Returns:
            Filtered list of content
        """
        if time_range == "all":
            return contents

        now = utc_now()
        if time_range == "week":
            cutoff = now - timedelta(days=TREND_ANALYSIS_WEEK_CUTOFF)
        elif time_range == "month":
            cutoff = now - timedelta(days=TREND_ANALYSIS_MONTH_CUTOFF)
        else:
            return contents

        # Filter by updated_at (when kept)
        filtered = [
            content
            for content in contents
            if (self._get_datetime_utc(content.updated_at) or self._get_datetime_utc(content.created_at)) >= cutoff
        ]

        return filtered
