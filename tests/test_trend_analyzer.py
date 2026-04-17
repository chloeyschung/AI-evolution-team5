"""Tests for trend analyzer (ADV-001)."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.ai.trend_analyzer import TrendAnalyzer, TrendFeedItem
from src.constants import ContentType
from src.data.models import Content, ContentStatus, SwipeAction, SwipeHistory
from src.data.repository import ContentRepository, SwipeRepository, ContentTagRepository, UserProfileRepository


@pytest.mark.asyncio
async def test_trend_analyzer_initialization(db_session):
    """Test trend analyzer initialization."""
    analyzer = TrendAnalyzer(db_session)
    assert analyzer._content_repo is not None
    assert analyzer._swipe_repo is not None
    assert analyzer._tag_repo is not None
    assert analyzer._user_profile_repo is not None


@pytest.mark.asyncio
async def test_get_trend_feed_empty(db_session):
    """Test trend feed with no kept content."""
    analyzer = TrendAnalyzer(db_session)
    items, total = await analyzer.get_trend_feed(user_id=999)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_trend_feed_minimal(db_session):
    """Test trend feed with less than 10 items (no scoring)."""
    analyzer = TrendAnalyzer(db_session)

    # Create 5 kept contents with swipe history
    now = datetime.now(timezone.utc)
    for i in range(5):
        kept_at = now - timedelta(days=i)
        content = Content(
            platform="YouTube",
            content_type=ContentType.VIDEO.value,  # Use string value
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            status=ContentStatus.ARCHIVED,  # Kept = archived
            updated_at=kept_at,  # Set timezone-aware datetime
            user_id=1,
        )
        db_session.add(content)
        await db_session.flush()  # Get content.id assigned

        # Add swipe history
        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=kept_at,
            user_id=1,
        )
        db_session.add(swipe)

    await db_session.commit()

    # Get trend feed
    items, total = await analyzer.get_trend_feed(user_id=1, limit=10)

    # Should return all items with neutral score
    assert total == 5
    assert len(items) == 5
    for item in items:
        assert item.relevance_score == TrendAnalyzer.DEFAULT_NEUTRAL_SCORE


@pytest.mark.asyncio
async def test_calculate_interest_match_score(db_session):
    """Test interest match score calculation."""
    analyzer = TrendAnalyzer(db_session)

    # Test with matching interests (case-insensitive)
    content_tags = ["artificial-intelligence", "technology", "tutorial"]
    user_interests = ["artificial-intelligence", "technology", "science"]

    score = analyzer._calculate_interest_match_score(content_tags, user_interests)

    # "artificial-intelligence" matches, "technology" matches
    # 2/3 = 0.666...
    assert score == pytest.approx(2/3, rel=0.01)

    # Test with no matches
    user_interests_no_match = ["cooking", "gardening"]
    score_no_match = analyzer._calculate_interest_match_score(content_tags, user_interests_no_match)
    assert score_no_match == 0

    # Test with no user interests (neutral)
    score_neutral = analyzer._calculate_interest_match_score(content_tags, [])
    assert score_neutral == TrendAnalyzer.DEFAULT_NEUTRAL_SCORE


@pytest.mark.asyncio
async def test_calculate_tag_similarity_score(db_session):
    """Test Jaccard similarity calculation."""
    analyzer = TrendAnalyzer(db_session)

    # Test with some overlap
    content_tags = ["ai", "tech", "tutorial"]
    preferred_tags = ["ai", "workflow", "tech"]

    # Jaccard = |{ai, tech}| / |{ai, tech, tutorial, workflow}| = 2/4 = 0.5
    score = analyzer._calculate_tag_similarity_score(content_tags, preferred_tags)
    assert score == pytest.approx(0.5, rel=0.01)

    # Test with no overlap
    preferred_tags_no_overlap = ["cooking", "gardening"]
    score_no_overlap = analyzer._calculate_tag_similarity_score(content_tags, preferred_tags_no_overlap)
    assert score_no_overlap == pytest.approx(0.0, rel=0.01)  # 0/5 = 0

    # Test with empty preferred tags (neutral)
    score_neutral = analyzer._calculate_tag_similarity_score(content_tags, [])
    assert score_neutral == TrendAnalyzer.DEFAULT_NEUTRAL_SCORE


@pytest.mark.asyncio
async def test_calculate_recency_score(db_session):
    """Test recency score calculation with decay."""
    analyzer = TrendAnalyzer(db_session)

    # Test with recent content (1 day ago)
    recent_content = Content(
        platform="YouTube",
        content_type=ContentType.VIDEO.value,
        url="https://youtube.com/watch?v=1",
        title="Recent Video",
        updated_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    recent_score = analyzer._calculate_recency_score(recent_content)
    # 1 / (1 + 1/30) = 0.9677
    assert recent_score == pytest.approx(0.9677, rel=0.01)
    assert recent_score > 0.9  # Recent should have high score

    # Test with old content (60 days ago)
    old_content = Content(
        platform="YouTube",
        content_type=ContentType.VIDEO.value,
        url="https://youtube.com/watch?v=2",
        title="Old Video",
        updated_at=datetime.now(timezone.utc) - timedelta(days=60),
    )
    old_score = analyzer._calculate_recency_score(old_content)
    # 1 / (1 + 60/30) = 0.333
    assert old_score == pytest.approx(0.333, rel=0.01)
    assert old_score < recent_score  # Old should have lower score


@pytest.mark.asyncio
async def test_filter_by_time_range(db_session):
    """Test time range filtering."""
    analyzer = TrendAnalyzer(db_session)

    # Create contents with different dates
    now = datetime.now(timezone.utc)
    contents = [
        Content(
            platform="YouTube",
            content_type=ContentType.VIDEO.value,
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            updated_at=now - timedelta(days=i * 10),
        )
        for i in range(10)
    ]

    # Test "all" - should return all
    filtered_all = analyzer._filter_by_time_range(contents, "all")
    assert len(filtered_all) == 10

    # Test "week" - should return only last 7 days
    filtered_week = analyzer._filter_by_time_range(contents, "week")
    assert len(filtered_week) == 1  # Only i=0 (0 days ago)

    # Test "month" - should return last 30 days
    filtered_month = analyzer._filter_by_time_range(contents, "month")
    assert len(filtered_month) == 3  # i=0, 1, 2 (0, 10, 20 days ago)


@pytest.mark.asyncio
async def test_get_preferred_tags(db_session):
    """Test getting preferred tags from kept content."""
    analyzer = TrendAnalyzer(db_session)

    # Create kept contents with tags
    contents = []
    for i in range(5):
        content = Content(
            platform="YouTube",
            content_type=ContentType.VIDEO.value,
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            status=ContentStatus.ARCHIVED,
            user_id=1,
        )
        db_session.add(content)
        await db_session.flush()  # Get content.id assigned
        contents.append(content)

        # Add swipe history
        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=datetime.now(timezone.utc) - timedelta(days=i),
            user_id=1,
        )
        db_session.add(swipe)

    await db_session.flush()

    # Add tags
    tag_repo = ContentTagRepository(db_session)
    await tag_repo.add_tags(contents[0].id, ["ai", "technology"])
    await tag_repo.add_tags(contents[1].id, ["ai", "programming"])
    await tag_repo.add_tags(contents[2].id, ["technology", "programming"])

    # Get preferred tags
    preferred_tags = await analyzer._get_preferred_tags(1)

    # Should have the most frequent tags
    assert len(preferred_tags) <= 10
    assert "ai" in preferred_tags or "technology" in preferred_tags or "programming" in preferred_tags


@pytest.mark.asyncio
async def test_trend_feed_item_creation():
    """Test TrendFeedItem creation."""
    content = Content(
        platform="YouTube",
        content_type=ContentType.VIDEO.value,
        url="https://youtube.com/watch?v=1",
        title="Test Video",
    )

    item = TrendFeedItem(
        content=content,
        relevance_score=0.85,
        matched_interests=["AI", "Technology"],
        top_tags=["artificial-intelligence", "technology"],
    )

    assert item.content == content
    assert item.relevance_score == 0.85
    assert item.matched_interests == ["AI", "Technology"]
    assert item.top_tags == ["artificial-intelligence", "technology"]


@pytest.mark.asyncio
async def test_engagement_score_with_no_history(db_session):
    """Test engagement score with no swipe history."""
    analyzer = TrendAnalyzer(db_session)

    score = await analyzer._calculate_engagement_score(
        content_tags=["ai", "tech"],
        user_id=999,  # User with no history
    )

    # Should return neutral score
    assert score == TrendAnalyzer.DEFAULT_NEUTRAL_SCORE


@pytest.mark.asyncio
async def test_score_threshold_filtering(db_session):
    """Test that items below min_score threshold are filtered out."""
    analyzer = TrendAnalyzer(db_session)

    # Create 15 kept contents (enough for scoring)
    now = datetime.now(timezone.utc)
    for i in range(15):
        kept_at = now - timedelta(days=i)
        content = Content(
            platform="YouTube",
            content_type=ContentType.VIDEO.value,
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            status=ContentStatus.ARCHIVED,
            updated_at=kept_at,
            user_id=1,
        )
        db_session.add(content)
        await db_session.flush()  # Get content.id assigned

        # Add swipe history
        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=kept_at,
            user_id=1,
        )
        db_session.add(swipe)

    await db_session.commit()

    # Get trend feed with high threshold
    items, total = await analyzer.get_trend_feed(
        user_id=1,
        limit=50,
        min_score=0.9,  # High threshold
    )

    # All items should have score >= 0.9
    for item in items:
        assert item.relevance_score >= 0.9


@pytest.mark.asyncio
async def test_pagination(db_session):
    """Test trend feed pagination."""
    analyzer = TrendAnalyzer(db_session)

    # Create 25 kept contents
    now = datetime.now(timezone.utc)
    for i in range(25):
        kept_at = now - timedelta(days=i)
        content = Content(
            platform="YouTube",
            content_type=ContentType.VIDEO.value,
            url=f"https://youtube.com/watch?v={i}",
            title=f"Video {i}",
            status=ContentStatus.ARCHIVED,
            updated_at=kept_at,
            user_id=1,
        )
        db_session.add(content)
        await db_session.flush()  # Get content.id assigned

        # Add swipe history
        swipe = SwipeHistory(
            content_id=content.id,
            action=SwipeAction.KEEP,
            swiped_at=kept_at,
            user_id=1,
        )
        db_session.add(swipe)

    await db_session.commit()

    # Get first page
    items1, total1 = await analyzer.get_trend_feed(user_id=1, limit=10, offset=0)
    assert len(items1) <= 10

    # Get second page
    items2, total2 = await analyzer.get_trend_feed(user_id=1, limit=10, offset=10)
    assert len(items2) <= 10

    # Totals should match
    assert total1 == total2

    # Items should be different (no overlap)
    ids1 = {item.content.id for item in items1}
    ids2 = {item.content.id for item in items2}
    assert ids1.isdisjoint(ids2)
