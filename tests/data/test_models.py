"""Tests for database models."""

import pytest
from src.data.models import Content, SwipeHistory, SwipeAction


class TestSwipeAction:
    """Tests for SwipeAction enum."""

    def test_keep_value(self):
        """Test KEEP action value."""
        assert SwipeAction.KEEP.value == "keep"

    def test_discard_value(self):
        """Test DISCARD action value."""
        assert SwipeAction.DISCARD.value == "discard"

    def test_is_str_enum(self):
        """Test that SwipeAction is a str enum."""
        assert isinstance(SwipeAction.KEEP, str)


class TestContentModel:
    """Tests for Content model."""

    def test_content_table_name(self):
        """Test Content table name."""
        assert Content.__tablename__ == "content"

    def test_content_has_required_fields(self):
        """Test Content has required fields."""
        assert hasattr(Content, "id")
        assert hasattr(Content, "platform")
        assert hasattr(Content, "content_type")
        assert hasattr(Content, "url")

    def test_content_has_optional_fields(self):
        """Test Content has optional fields."""
        assert hasattr(Content, "title")
        assert hasattr(Content, "author")
        assert hasattr(Content, "timestamp")
        assert hasattr(Content, "created_at")

    def test_content_has_relationship(self):
        """Test Content has swipe_history relationship."""
        assert hasattr(Content, "swipe_history")


class TestSwipeHistoryModel:
    """Tests for SwipeHistory model."""

    def test_swipe_history_table_name(self):
        """Test SwipeHistory table name."""
        assert SwipeHistory.__tablename__ == "swipe_history"

    def test_swipe_history_has_required_fields(self):
        """Test SwipeHistory has required fields."""
        assert hasattr(SwipeHistory, "id")
        assert hasattr(SwipeHistory, "content_id")
        assert hasattr(SwipeHistory, "action")
        assert hasattr(SwipeHistory, "swiped_at")

    def test_swipe_history_has_relationship(self):
        """Test SwipeHistory has content relationship."""
        assert hasattr(SwipeHistory, "content")
