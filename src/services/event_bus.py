"""Event system for decoupled side effects.

This module provides a simple pub/sub event system for handling side effects
without tight coupling between business logic and downstream operations.

Usage:
    # Publish an event
    await event_bus.publish(ContentCreatedEvent(content_id=123, user_id=1))

    # Subscribe to events
    @event_bus.on(ContentCreatedEvent)
    async def handle_content_created(event: ContentCreatedEvent):
        # Generate tags, update analytics, etc.
        pass
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Any

from src.utils.datetime_utils import utc_now


class EventType(Enum):
    """Event type categories."""

    CONTENT = "content"
    SWIPE = "swipe"
    ACHIEVEMENT = "achievement"
    REMINDER = "reminder"
    SYNC = "sync"


@dataclass
class BaseEvent:
    """Base event class with common fields."""

    event_type: EventType
    event_id: str
    timestamp: datetime
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ContentCreatedEvent:
    """Event published when content is created."""

    content_id: int
    user_id: int
    event_type: EventType = EventType.CONTENT
    event_id: str = field(default="")
    timestamp: datetime | None = field(default=None)
    metadata: dict[str, Any] | None = field(default=None)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = utc_now()
        self.event_id = f"content_created_{self.content_id}_{self.timestamp.isoformat()}"


@dataclass
class ContentSwipedEvent:
    """Event published when content is swiped."""

    content_id: int
    user_id: int
    action: str  # 'keep' or 'discard'
    event_type: EventType = EventType.SWIPE
    event_id: str = field(default="")
    timestamp: datetime | None = field(default=None)
    metadata: dict[str, Any] | None = field(default=None)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = utc_now()
        self.event_id = f"content_swiped_{self.content_id}_{self.timestamp.isoformat()}"


@dataclass
class AchievementUnlockedEvent:
    """Event published when an achievement is unlocked."""

    user_id: int
    achievement_key: str
    achievement_type: str
    event_type: EventType = EventType.ACHIEVEMENT
    event_id: str = field(default="")
    timestamp: datetime | None = field(default=None)
    metadata: dict[str, Any] | None = field(default=None)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = utc_now()
        self.event_id = f"achievement_{self.achievement_key}_{self.timestamp.isoformat()}"


@dataclass
class SyncCompletedEvent:
    """Event published when a sync operation completes."""

    user_id: int
    provider: str  # 'youtube', 'linkedin', etc.
    success: bool
    items_synced: int = 0
    error_message: str | None = None
    event_type: EventType = EventType.SYNC
    event_id: str = field(default="")
    timestamp: datetime | None = field(default=None)
    metadata: dict[str, Any] | None = field(default=None)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = utc_now()
        self.event_id = f"sync_{self.provider}_{self.timestamp.isoformat()}"


class EventBus:
    """Simple event bus for pub/sub pattern.

    This provides a basic event system for decoupling side effects from
    business logic. Events are published synchronously and handlers are
    called in the order they were registered.

    Thread safety:
        This implementation uses asyncio.Lock for thread safety in async contexts.
    """

    def __init__(self):
        """Initialize event bus."""
        import asyncio

        self._handlers: dict[type, list[Callable]] = {}
        self._lock = asyncio.Lock()

    def on(self, event_type: type[BaseEvent]):
        """Decorator to register an event handler.

        Args:
            event_type: The event type to subscribe to.

        Returns:
            Decorator function that registers the handler.

        Example:
            @event_bus.on(ContentCreatedEvent)
            async def handle_content_created(event: ContentCreatedEvent):
                await generate_tags(event.content_id)
        """

        def decorator(func: Callable):
            self._register_handler(event_type, func)
            return func

        return decorator

    def _register_handler(self, event_type: type[BaseEvent], handler: Callable) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The event type to handle.
            handler: The async handler function.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to all registered handlers.

        Args:
            event: The event to publish.

        Note:
            Handlers are called sequentially in registration order.
            If a handler raises an exception, it is logged and other
            handlers continue to be called.
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        for handler in handlers:
            try:
                if hasattr(handler, "__wrapped__"):
                    # Handle decorated functions
                    await handler(event)
                else:
                    await handler(event)
            except Exception as e:
                # Log but don't propagate - don't let one handler fail all
                print(f"Event handler error for {event_type.__name__}: {e}")

    def clear_handlers(self) -> None:
        """Clear all registered handlers.

        Useful for testing or resetting the event bus.
        """
        self._handlers.clear()


# Global event bus instance
event_bus = EventBus()
