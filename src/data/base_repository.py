"""Base repository class with common patterns."""

from typing import Generic, Optional, TypeVar, Callable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    """Base repository providing common database operations.

    This class consolidates repeated patterns found across repositories:
    - get_or_create: Get existing record or create with defaults
    - get_by_id: Fetch record by primary key
    - get_by_field: Fetch record by a specific field value
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize repository with database session.

        Args:
            db_session: Async database session.
        """
        self.session = db_session

    async def get_by_id(self, model: type[ModelType], id_value: int) -> Optional[ModelType]:
        """Get a record by its primary key.

        Args:
            model: SQLAlchemy model class.
            id_value: Primary key value.

        Returns:
            Model instance if found, None otherwise.
        """
        result = await self.session.execute(
            select(model).where(model.id == id_value)
        )
        return result.scalar_one_or_none()

    async def _get_or_create_base(
        self,
        model: type[ModelType],
        where_clause: any,
        defaults: Callable[[], dict],
    ) -> ModelType:
        """Get existing record or create new one with defaults (internal).

        This consolidates the repeated get-or-create pattern found across
        multiple repositories (StreakRepository, ReminderPreferenceRepository,
        UserActivityPatternRepository, UserProfileRepository).

        Args:
            model: SQLAlchemy model class.
            where_clause: SQLAlchemy where clause for querying.
            defaults: Callable that returns dict of default values for creation.

        Returns:
            Existing or newly created model instance.
        """
        # Query for existing record
        result = await self.session.execute(select(model).where(where_clause))
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create with defaults
        new_record = model(**defaults())
        self.session.add(new_record)
        await self.session.commit()
        await self.session.refresh(new_record)

        return new_record
