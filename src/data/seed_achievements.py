"""Seed achievement definitions for gamified system (ADV-002)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AchievementDefinition

ACHIEVEMENT_DEFINITIONS = [
    # Streak achievements
    {
        "key": "streak_1",
        "type": "streak",
        "name": "First Steps",
        "description": "Complete your first day of content consumption",
        "icon": "🌱",
        "trigger_value": 1,
    },
    {
        "key": "streak_3",
        "type": "streak",
        "name": "Building Momentum",
        "description": "Maintain a 3-day streak of content consumption",
        "icon": "🔥",
        "trigger_value": 3,
    },
    {
        "key": "streak_7",
        "type": "streak",
        "name": "On Fire",
        "description": "Maintain a 7-day streak of content consumption",
        "icon": "🔥🔥",
        "trigger_value": 7,
    },
    {
        "key": "streak_14",
        "type": "streak",
        "name": "Unstoppable",
        "description": "Maintain a 14-day streak of content consumption",
        "icon": "🔥🔥🔥",
        "trigger_value": 14,
    },
    {
        "key": "streak_30",
        "type": "streak",
        "name": "Legend",
        "description": "Maintain a 30-day streak of content consumption",
        "icon": "👑",
        "trigger_value": 30,
    },
    # Volume achievements
    {
        "key": "volume_10",
        "type": "volume",
        "name": "Beginner",
        "description": "Complete your first 10 content swipes",
        "icon": "📚",
        "trigger_value": 10,
    },
    {
        "key": "volume_50",
        "type": "volume",
        "name": "Enthusiast",
        "description": "Complete 50 content swipes",
        "icon": "📖",
        "trigger_value": 50,
    },
    {
        "key": "volume_100",
        "type": "volume",
        "name": "Scholar",
        "description": "Complete 100 content swipes",
        "icon": "🎓",
        "trigger_value": 100,
    },
    {
        "key": "volume_500",
        "type": "volume",
        "name": "Expert",
        "description": "Complete 500 content swipes",
        "icon": "🏆",
        "trigger_value": 500,
    },
    {
        "key": "volume_1000",
        "type": "volume",
        "name": "Master",
        "description": "Complete 1000 content swipes",
        "icon": "💎",
        "trigger_value": 1000,
    },
    # Diversity achievements
    {
        "key": "diversity_3",
        "type": "diversity",
        "name": "Explorer",
        "description": "Save content from 3 different platforms",
        "icon": "🌍",
        "trigger_value": 3,
    },
    {
        "key": "diversity_5",
        "type": "diversity",
        "name": "Polyglot",
        "description": "Save content from 5 different platforms",
        "icon": "🌐",
        "trigger_value": 5,
    },
    {
        "key": "diversity_8",
        "type": "diversity",
        "name": "Omni",
        "description": "Save content from 8+ different platforms",
        "icon": "✨",
        "trigger_value": 8,
    },
    # Curation achievements
    {
        "key": "curation_20",
        "type": "curation",
        "name": "Curator",
        "description": "Keep your first 20 pieces of content",
        "icon": "⭐",
        "trigger_value": 20,
    },
    {
        "key": "curation_100",
        "type": "curation",
        "name": "Collector",
        "description": "Keep 100 pieces of content",
        "icon": "📦",
        "trigger_value": 100,
    },
    {
        "key": "curation_500",
        "type": "curation",
        "name": "Archivist",
        "description": "Keep 500 pieces of content",
        "icon": "🏛️",
        "trigger_value": 500,
    },
]


async def seed_achievements(db_session: AsyncSession) -> int:
    """Seed achievement definitions into database.

    Args:
        db_session: Async database session

    Returns:
        Number of achievements created
    """
    # Check if already seeded
    result = await db_session.execute(select(AchievementDefinition))
    existing = result.scalars().all()

    if existing:
        return 0

    # Seed achievements
    created = 0
    for achievement_data in ACHIEVEMENT_DEFINITIONS:
        achievement = AchievementDefinition(
            key=achievement_data["key"],
            type=achievement_data["type"],
            name=achievement_data["name"],
            description=achievement_data["description"],
            icon=achievement_data["icon"],
            trigger_value=achievement_data["trigger_value"],
            is_active=1,
        )
        db_session.add(achievement)
        created += 1

    await db_session.flush()
    return created
