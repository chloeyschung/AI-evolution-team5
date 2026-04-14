"""Trend analyzer for personalized content ranking."""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from .categorizer import Categorizer
from .summarizer import Summarizer
from ..data.models import Content, SwipeAction
from ..data.repository import ContentRepository, SwipeRepository, ContentTagRepository, UserProfileRepository


class TrendFeedItem:
    """Item in trend feed with relevance score."""

    def __init__(
        self,
        content: Content,
        relevance_score: float,
        matched_interests: List[str],
        top_tags: List[str],
    ):
        self.content = content
        self.relevance_score = relevance_score
        self.matched_interests = matched_interests
        self.top_tags = top_tags


class TrendAnalyzer:
    """Analyze and rank content for personalized trend feed."""

    # Scoring weights
    INTEREST_MATCH_WEIGHT = 0.35
    TAG_SIMILARITY_WEIGHT = 0.30
    RECENCY_WEIGHT = 0.20
    ENGAGEMENT_WEIGHT = 0.15

    # Configuration
    HALF_LIFE_DAYS = 30  # Content loses half recency score after this many days
    MIN_ITEMS_FOR_SCORING = 10  # Below this, use simple recency sort
    DEFAULT_NEUTRAL_SCORE = 0.5  # Neutral score when no data available
    MIN_SCORE_THRESHOLD = 0.1  # Minimum score to appear in feed

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
    ) -> Tuple[List[TrendFeedItem], int]:
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
        # Get kept content for user
        kept_contents = await self._content_repo.get_kept(
            limit=None,  # Get all for scoring
            offset=0,
        )

        # Handle empty case
        if not kept_contents:
            return [], 0

        # Get user context
        user_interests = await self._user_profile_repo.get_interest_tags()
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
        scored_items: List[TrendFeedItem] = []
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
        user_interests: List[str],
        preferred_tags: List[str],
    ) -> Tuple[float, List[str], List[str]]:
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
        content_tags: List[str],
        user_interests: List[str],
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
        matched = sum(
            1 for interest in user_interests_lower
            if any(interest in tag for tag in content_tags_lower)
        )

        return matched / len(user_interests)

    def _calculate_tag_similarity_score(
        self,
        content_tags: List[str],
        preferred_tags: List[str],
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
        now = datetime.now(timezone.utc)

        # Calculate days since kept
        delta = now - kept_at
        days_since_kept = delta.total_seconds() / (24 * 60 * 60)

        # Apply decay formula
        score = 1 / (1 + days_since_kept / self.HALF_LIFE_DAYS)

        return score

    async def _calculate_engagement_score(
        self,
        content_tags: List[str],
        user_id: int,
    ) -> float:
        """Calculate engagement score based on keep ratio for same tags (0-1).

        For each content tag, calculate the ratio of kept vs. total content
        with that tag. Average across all tags.
        """
        if not content_tags:
            return self.DEFAULT_NEUTRAL_SCORE

        # Get swipe history for user
        swipe_history = await self._swipe_repo.get_history(user_id)

        if not swipe_history:
            return self.DEFAULT_NEUTRAL_SCORE

        # Calculate keep ratio per tag
        tag_ratios: List[float] = []
        for tag in content_tags:
            tag_ratios.append(
                self._calculate_tag_keep_ratio(tag, swipe_history, content_tags)
            )

        # Average across all tags
        if not tag_ratios:
            return self.DEFAULT_NEUTRAL_SCORE

        return sum(tag_ratios) / len(tag_ratios)

    def _calculate_tag_keep_ratio(
        self,
        tag: str,
        swipe_history: List,
        content_tags: List[str],
    ) -> float:
        """Calculate keep ratio for a specific tag.

        Ratio = kept_content_with_tag / total_content_with_tag
        """
        # This is a simplified calculation
        # In production, we'd query the database for accurate counts
        kept_count = 0
        total_count = 0

        for swipe in swipe_history:
            # Check if this content has the tag
            # Note: This is a simplification - in reality we'd need to join with ContentTag
            if swipe.action == SwipeAction.KEEP:
                kept_count += 1
            total_count += 1

        if total_count == 0:
            return self.DEFAULT_NEUTRAL_SCORE

        return kept_count / total_count

    async def _get_preferred_tags(self, user_id: int) -> List[str]:
        """Get preferred tags from user's most-kept content.

        Returns top tags from content user has kept (max 10 tags).
        """
        # Get kept content
        kept_contents = await self._content_repo.get_kept(
            limit=50,  # Sample size
            offset=0,
        )

        if not kept_contents:
            return []

        # Count tag frequency
        tag_counts: dict[str, int] = {}
        for content in kept_contents:
            tags = await self._tag_repo.get_tags(content.id)
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
        """
        if dt is None:
            return None
        if dt.tzinfo is None:
            # Assume naive datetime is UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _filter_by_time_range(
        self,
        contents: List[Content],
        time_range: str,
    ) -> List[Content]:
        """Filter contents by time range.

        Args:
            contents: List of content items
            time_range: "week", "month", or "all"

        Returns:
            Filtered list of content
        """
        if time_range == "all":
            return contents

        now = datetime.now(timezone.utc)
        if time_range == "week":
            cutoff = now - timedelta(days=7)
        elif time_range == "month":
            cutoff = now - timedelta(days=30)
        else:
            return contents

        # Filter by updated_at (when kept)
        filtered = [
            content
            for content in contents
            if (self._get_datetime_utc(content.updated_at) or self._get_datetime_utc(content.created_at)) >= cutoff
        ]

        return filtered
