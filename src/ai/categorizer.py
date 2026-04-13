"""AI-powered content categorization using LLM.

Auto-generates 1-3 category tags for content based on title and summary.
"""

import re
from typing import List, Optional

from src.ai.summarizer import Summarizer


class CategorizationError(Exception):
    """Base exception for categorization errors."""
    pass


class Categorizer:
    """AI-powered content categorization.

    Generates 1-3 relevant category tags for content using LLM.
    """

    # Max tags per content
    MAX_TAGS = 3

    # Max characters per tag
    MAX_TAG_LENGTH = 50

    def __init__(self, summarizer: Summarizer):
        """Initialize categorizer.

        Args:
            summarizer: Summarizer instance for LLM calls.
        """
        self.summarizer = summarizer

    async def generate_tags(
        self, title: str, summary: Optional[str] = None
    ) -> List[str]:
        """Generate category tags for content.

        Args:
            title: Content title.
            summary: Content summary (optional).

        Returns:
            List of 1-3 category tags (lowercase, cleaned).
        """
        # Build prompt for tag generation
        prompt = self._build_tag_prompt(title, summary)

        try:
            # Call LLM for tag generation
            response = await self.summarizer.generate_summary(prompt)

            # Parse and clean tags from response
            tags = self._parse_tags(response)

            return tags

        except Exception as e:
            # Log error and return empty list (don't block content save)
            print(f"Tag generation failed: {e}")
            return []

    def _build_tag_prompt(self, title: str, summary: Optional[str]) -> str:
        """Build prompt for tag generation.

        Args:
            title: Content title.
            summary: Content summary.

        Returns:
            Prompt string for LLM.
        """
        summary_text = summary or "No summary available."

        prompt = f"""Analyze this content and generate 1-3 category tags.

Title: {title}
Summary: {summary_text}

Rules:
- Generate 1-3 tags maximum
- Each tag should be 1-3 words
- Use lowercase, no special characters
- Only include the most relevant categories
- Tags should be diverse (not overlapping)

Output format: Just list the tags, one per line, no numbers or bullets.

Tags:"""

        return prompt

    def _parse_tags(self, response: str) -> List[str]:
        """Parse tags from LLM response.

        Args:
            response: LLM response text.

        Returns:
            List of cleaned, validated tags.
        """
        tags = []

        # Split by newlines or commas
        parts = re.split(r'[\n,]+', response.strip())

        for part in parts:
            # Clean the tag
            tag = self._clean_tag(part.strip())

            # Validate and add
            if tag and len(tags) < self.MAX_TAGS:
                tags.append(tag)

                # Stop if we have max tags
                if len(tags) >= self.MAX_TAGS:
                    break

        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags

    def _clean_tag(self, tag: str) -> str:
        """Clean and validate a tag.

        Args:
            tag: Raw tag string.

        Returns:
            Cleaned tag or empty string if invalid.
        """
        # Remove special characters, keep letters, numbers, spaces, hyphens
        cleaned = re.sub(r'[^\w\s\-]', '', tag)

        # Lowercase and strip
        cleaned = cleaned.lower().strip()

        # Remove numbering (1., 2-, etc.)
        cleaned = re.sub(r'^\d+[\.\-\)]\s*', '', cleaned)

        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Validate length
        if len(cleaned) > self.MAX_TAG_LENGTH:
            cleaned = cleaned[: self.MAX_TAG_LENGTH]

        # Must have at least one word
        if not cleaned or len(cleaned.split()) == 0:
            return ""

        return cleaned
