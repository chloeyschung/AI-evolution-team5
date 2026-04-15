"""Service layer for business logic.

This package contains service classes that encapsulate business logic,
separating concerns from the API layer (routes) and data access layer (repositories).

Services:
    - ContentService: Content CRUD and management operations
    - SwipeService: Swipe action recording and history
    - EventBus: Event system for decoupled side effects
"""

from .content_service import ContentService
from .event_bus import (
    EventBus,
    BaseEvent,
    ContentCreatedEvent,
    ContentSwipedEvent,
    AchievementUnlockedEvent,
    SyncCompletedEvent,
    event_bus,
)
from .swipe_service import BatchSwipeResult, SwipeResult, SwipeService

__all__ = [
    "ContentService",
    "SwipeService",
    "SwipeResult",
    "BatchSwipeResult",
    "EventBus",
    "BaseEvent",
    "ContentCreatedEvent",
    "ContentSwipedEvent",
    "AchievementUnlockedEvent",
    "SyncCompletedEvent",
    "event_bus",
]
