"""Swipe service for handling swipe action business logic.

This module contains business logic for swipe operations, separating concerns
from the API layer and repository layer.
"""

from dataclasses import dataclass, field

from src.data.models import SwipeAction
from src.data.repository import ContentRepository, SwipeRepository
from .event_bus import ContentSwipedEvent, event_bus


@dataclass
class SwipeResult:
    """Result of a swipe action."""

    id: int
    content_id: int
    action: SwipeAction


@dataclass
class BatchSwipeResult:
    """Result of a batch swipe operation."""

    recorded: int
    results: list[SwipeResult] = field(default_factory=list)


class SwipeService:
    """Service layer for swipe business logic.

    This service handles swipe recording and related operations,
    keeping business logic separate from API routes.
    """

    def __init__(self, db_session):
        """Initialize swipe service.

        Args:
            db_session: Async database session.
        """
        self._content_repo = ContentRepository(db_session)
        self._swipe_repo = SwipeRepository(db_session)
        self._event_bus = event_bus

    async def _assert_content_owned(self, content_id: int, user_id: int) -> None:
        """Ensure the referenced content exists and belongs to the actor."""
        content = await self._content_repo.get_by_id(content_id)
        if content is None or content.user_id != user_id:
            raise ValueError("content_not_found")

    async def record_swipe(
        self,
        content_id: int,
        action: SwipeAction,
        user_id: int,
    ) -> SwipeResult:
        """Record a single swipe action.

        Args:
            content_id: Content ID being swiped.
            action: Swipe action (keep or discard).
            user_id: User ID of the swipe actor.

        Returns:
            Swipe result with ID and action.
        """
        await self._assert_content_owned(content_id, user_id)
        history = await self._swipe_repo.record_swipe(content_id, action, user_id)

        # Publish event for side effects (achievement checking, analytics, etc.)
        await self._event_bus.publish(
            ContentSwipedEvent(
                content_id=content_id,
                user_id=user_id,
                action=action.value,
            )
        )

        return SwipeResult(
            id=history.id,
            content_id=history.content_id,
            action=history.action,
        )

    async def record_swipes_batch(
        self,
        actions: list[tuple[int, SwipeAction]],
        user_id: int,
    ) -> BatchSwipeResult:
        """Record multiple swipe actions atomically.

        Args:
            actions: List of (content_id, action) tuples.
            user_id: User ID of the swipe actor.

        Returns:
            Batch swipe result with count and individual results.
        """
        # Validate ownership for every content reference before mutating any rows.
        # This keeps batch behavior atomic from an authorization perspective.
        for content_id, _action in actions:
            await self._assert_content_owned(content_id, user_id)
        histories = await self._swipe_repo.record_swipes_batch(actions, user_id)

        # Publish events for each swipe (for side effects)
        for history in histories:
            await self._event_bus.publish(
                ContentSwipedEvent(
                    content_id=history.content_id,
                    user_id=user_id,
                    action=history.action.value,
                )
            )

        results = [
            SwipeResult(
                id=h.id,
                content_id=h.content_id,
                action=h.action,
            )
            for h in histories
        ]
        return BatchSwipeResult(recorded=len(histories), results=results)

    async def get_swipe_history(
        self,
        user_id: int,
        content_id: int | None = None,
        limit: int | None = None,
    ) -> list[SwipeResult]:
        """Get swipe history scoped to a user.

        Args:
            user_id: The user whose history to retrieve.
            content_id: Optional content ID to filter by.
            limit: Optional limit on results.

        Returns:
            List of swipe results.
        """
        histories = await self._swipe_repo.get_all_history(user_id=user_id, content_id=content_id, limit=limit)
        return [
            SwipeResult(
                id=h.id,
                content_id=h.content_id,
                action=h.action,
            )
            for h in histories
        ]
