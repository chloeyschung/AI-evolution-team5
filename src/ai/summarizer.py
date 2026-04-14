import asyncio
import httpx
from .exceptions import SummarizationError, APIConnectionError, InvalidResponseError


class Summarizer:
    DEFAULT_MODEL = "claude-3-5-sonnet-20240620"
    DEFAULT_MAX_TOKENS = 300
    DEFAULT_TIMEOUT = 30.0
    ANTHROPIC_VERSION = "2023-06-01"
    CONTENT_TYPE_JSON = "application/json"

    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com/v1/messages"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": self.CONTENT_TYPE_JSON,
        }

    def _build_prompt(self, content: str, max_lines: int) -> str:
        """Build the prompt for summarization."""
        return (
            f"You are an expert summarizer. Your task is to summarize the following content "
            f"into exactly {max_lines} lines. Ensure the summary is high-density, "
            f"avoids fluff, and preserves the core context (Who, What, Why).\n\n"
            f"CONTENT:\n{content}"
        )

    async def summarize(self, content: str, max_lines: int = 3, max_retries: int = 3) -> str:
        """
        Generates a concise summary of the provided content.

        Args:
            content: The raw text to be summarized.
            max_lines: The maximum number of lines for the summary.
            max_retries: Maximum number of retry attempts for transient errors.

        Returns:
            A string containing the summarized text.

        Raises:
            SummarizationError: If the service fails to generate a valid summary.
        """
        if not content or not content.strip():
            raise SummarizationError("Input content is empty.")

        prompt = self._build_prompt(content, max_lines)
        payload = {
            "model": self.DEFAULT_MODEL,
            "max_tokens": self.DEFAULT_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }

        last_error = None

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        self.base_url,
                        headers=self.headers,
                        json=payload,
                        timeout=self.DEFAULT_TIMEOUT,
                    )

                    if response.status_code >= 500 and attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue

                    if response.status_code != 200:
                        raise APIConnectionError(f"API request failed with status {response.status_code}: {response.text}")

                    data = response.json()

                    try:
                        summary = data["content"][0]["text"].strip()
                    except (KeyError, IndexError):
                        raise InvalidResponseError("Unexpected API response format.")

                    lines = summary.split("\n")
                    if len(lines) > max_lines:
                        summary = "\n".join(lines[:max_lines])

                    # Enforce 300-character limit with word-boundary truncation (AI-001 spec)
                    if len(summary) > 300:
                        # Truncate to word boundary, no trailing ellipsis
                        truncated = summary[:300]
                        # Find last space to avoid cutting words
                        last_space = truncated.rfind(' ')
                        if last_space > 200:  # Ensure we have at least 200 chars
                            summary = truncated[:last_space]
                        else:
                            summary = truncated

                    return summary

                except (APIConnectionError, InvalidResponseError):
                    # Don't retry domain-specific errors, raise immediately
                    raise
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise APIConnectionError(f"Request failed: {exc}")
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise SummarizationError(f"Unexpected error: {e}")

        raise SummarizationError(f"All {max_retries} retry attempts failed. Last error: {last_error}")
