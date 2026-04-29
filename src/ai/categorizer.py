"""AI-powered content categorization using LLM.

Auto-generates 1-3 category tags for content based on title and summary.

TODO #10 (2026-04-14): Removed Optional import - using | None syntax instead.
TODO #15 (2026-04-14): Added complete docstrings to methods.
TODO #13 (2026-04-14): Moved magic numbers to constants.py
"""

import re

from src.ai.summarizer import Summarizer
from src.constants import MAX_TAG_LENGTH, MAX_TAGS_PER_CONTENT


class CategorizationError(Exception):
    """Base exception for categorization errors."""

    pass


class Categorizer:
    """AI-powered content categorization.

    Generates 1-3 relevant category tags for content using LLM.
    """

    def __init__(self, summarizer: Summarizer):
        """Initialize categorizer.

        Args:
            summarizer: Summarizer instance for LLM calls.
        """
        self.summarizer = summarizer

    async def generate_tags(self, title: str, summary: str | None = None) -> list[str]:
        """Generate category tags for content using LLM.

        Args:
            title: Content title. Required for tag generation.
            summary: Content summary (optional). Improves tag accuracy when provided.

        Returns:
            List of 1-3 category tags (lowercase, cleaned). Returns empty list if
            tag generation fails (won't block content save).

        Example:
            >>> categorizer = Categorizer(summarizer)
            >>> tags = await categorizer.generate_tags("Python Tips", "Learn Python...")
            >>> print(tags)  # ['python', 'programming', 'tutorial']
        """
        # Build prompt for tag generation
        prompt = self._build_tag_prompt(title, summary)

        try:
            # Call LLM for tag generation
            response = await self.summarizer.summarize(prompt)

            # Parse and clean tags from response
            tags = self._parse_tags(response)

            return tags

        except Exception as e:
            # Log error and return empty list (don't block content save)
            import logging

            logging.warning(f"Tag generation failed: {e}")
            return []

    def _build_tag_prompt(self, title: str, summary: str | None) -> str:
        """Build prompt for tag generation.

        Constructs a structured prompt with title and summary to guide
        the LLM in generating relevant category tags.

        Args:
            title: Content title. Required for prompt construction.
            summary: Content summary. If None, uses "No summary available."

        Returns:
            Formatted prompt string ready for LLM consumption.

        Example:
            >>> prompt = categorizer._build_tag_prompt("Python Tips", "Learn Python...")
            >>> print(prompt[:50])  # "Analyze this content and generate 1-3 cat..."
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

    def _parse_tags(self, response: str) -> list[str]:
        """Parse tags from LLM response.

        Splits response by newlines/commas, cleans each tag, removes
        duplicates while preserving order, and returns up to MAX_TAGS.

        Args:
            response: Raw LLM response text. Can contain newlines, commas,
                numbering (1., 2-), or bullets.

        Returns:
            List of 1-3 cleaned, validated, unique tags in order of appearance.
            Empty list if no valid tags found.

        Example:
            >>> response = "1. python\\n2. programming\\n3. tutorial"
            >>> tags = categorizer._parse_tags(response)
            >>> print(tags)  # ['python', 'programming', 'tutorial']
        """
        tags = []

        # Split by newlines or commas
        parts = re.split(r"[\n,]+", response.strip())

        for part in parts:
            # Clean the tag
            tag = self._clean_tag(part.strip())

            # Validate and add
            if tag and len(tags) < MAX_TAGS_PER_CONTENT:
                tags.append(tag)

                # Stop if we have max tags
                if len(tags) >= MAX_TAGS_PER_CONTENT:
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

        Removes special characters, normalizes to lowercase, strips numbering
        (1., 2-), collapses spaces, and enforces MAX_TAG_LENGTH limit.

        Args:
            tag: Raw tag string. May contain special characters, numbering,
                or extra whitespace.

        Returns:
            Cleaned tag with only letters, numbers, spaces, and hyphens.
            Empty string if tag is invalid (empty after cleaning or no words).

        Example:
            >>> categorizer._clean_tag("1. Python-Tips!")  # 'python-tips'
            >>> categorizer._clean_tag("  2-  PROBLEM  ")  # 'problem'
        """
        # Remove special characters, keep letters, numbers, spaces, hyphens
        cleaned = re.sub(r"[^\w\s\-]", "", tag)

        # Lowercase and strip
        cleaned = cleaned.lower().strip()

        # Remove numbering (1., 2-, etc.)
        cleaned = re.sub(r"^\d+[\.\-\)]\s*", "", cleaned)

        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Validate length
        if len(cleaned) > MAX_TAG_LENGTH:
            cleaned = cleaned[:MAX_TAG_LENGTH]

        # Must have at least one word
        if not cleaned or len(cleaned.split()) == 0:
            return ""

        return cleaned
