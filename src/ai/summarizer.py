import asyncio
from urllib.parse import urlencode

import httpx

from src.utils.http_client import async_client_context

from .exceptions import APIConnectionError, InvalidResponseError, SummarizationError


class Summarizer:
    DEFAULT_MODEL = "claude-3-5-sonnet-20240620"
    DEFAULT_MAX_TOKENS = 120
    DEFAULT_TIMEOUT = 30.0
    ANTHROPIC_VERSION = "2023-06-01"
    CONTENT_TYPE_JSON = "application/json"
    PROVIDERS = {"anthropic", "openai", "gemini", "auto"}

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1/messages",
        model: str | None = None,
        provider: str = "auto",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model or self.DEFAULT_MODEL
        provider = provider.strip().lower()
        self.provider = provider if provider in self.PROVIDERS else "auto"

    def _resolved_provider(self) -> str:
        if self.provider != "auto":
            return self.provider

        base = self.base_url.lower()
        if "generativelanguage.googleapis.com" in base or ":generatecontent" in base:
            return "gemini"
        if "/chat/completions" in base or "/v1/responses" in base:
            return "openai"
        return "anthropic"

    def _anthropic_request(self, prompt: str) -> tuple[str, dict[str, str], dict]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": self.CONTENT_TYPE_JSON,
        }
        payload = {
            "model": self.model,
            "max_tokens": self.DEFAULT_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        return self.base_url, headers, payload

    def _openai_request(self, prompt: str) -> tuple[str, dict[str, str], dict]:
        headers = {
            "content-type": self.CONTENT_TYPE_JSON,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "max_tokens": self.DEFAULT_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
            # For reasoning-enabled models (e.g., Qwen3.x on vLLM),
            # force direct answer tokens so short summaries are returned.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        return self.base_url, headers, payload

    def _gemini_request(self, prompt: str) -> tuple[str, dict[str, str], dict]:
        url = self.base_url
        if ":generateContent" not in url:
            url = url.rstrip("/") + f"/v1beta/models/{self.model}:generateContent"
        if "key=" not in url and self.api_key:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{urlencode({'key': self.api_key})}"

        headers = {"content-type": self.CONTENT_TYPE_JSON}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": self.DEFAULT_MAX_TOKENS},
        }
        return url, headers, payload

    def _build_request(self, prompt: str) -> tuple[str, dict[str, str], dict, str]:
        provider = self._resolved_provider()
        if provider == "openai":
            url, headers, payload = self._openai_request(prompt)
            return url, headers, payload, provider
        if provider == "gemini":
            url, headers, payload = self._gemini_request(prompt)
            return url, headers, payload, provider
        url, headers, payload = self._anthropic_request(prompt)
        return url, headers, payload, "anthropic"

    def _extract_summary(self, data: dict, provider: str) -> str:
        try:
            if provider == "openai":
                message = data["choices"][0]["message"]["content"]
                if message is None:
                    raise InvalidResponseError("OpenAI response did not include message content.")
                if isinstance(message, list):
                    text_parts = [part.get("text", "") for part in message if isinstance(part, dict)]
                    return "".join(text_parts).strip()
                return str(message).strip()

            if provider == "gemini":
                parts = data["candidates"][0]["content"]["parts"]
                text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
                return "".join(text_parts).strip()

            for block in data.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str) and text.strip():
                        return text.strip()
            raise InvalidResponseError("Anthropic response did not include a text block.")
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            raise InvalidResponseError("Unexpected API response format.") from e

    @staticmethod
    def _anthropic_has_text_block(data: dict) -> bool:
        content = data.get("content")
        if not isinstance(content, list):
            return False
        return any(
            isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
            and block.get("text").strip()
            for block in content
        )

    def _build_prompt(self, content: str, max_lines: int) -> str:
        """Build the prompt for summarization."""
        return (
            f"Summarize as exactly {max_lines} bullet points.\n"
            f"Rules:\n"
            f"- Start each bullet with '• '\n"
            f"- Max 70 characters per bullet — be ruthlessly brief\n"
            f"- One concrete fact per bullet: who/what/why, no filler\n"
            f"- Output ONLY the {max_lines} bullets, nothing else\n\n"
            f"CONTENT:\n{content}"
        )

    @staticmethod
    def _build_title_prompt(content: str) -> str:
        return (
            "Create one concise, searchable title for the content below.\n"
            "Rules:\n"
            "- 8 to 16 words\n"
            "- Plain ASCII-friendly wording\n"
            "- No emoji, no hashtags, no trailing site suffixes\n"
            "- Preserve key entities and topic\n"
            "- Output ONLY the title line\n\n"
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
        request_url, headers, payload, provider = self._build_request(prompt)

        last_error = None

        async with async_client_context() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        request_url,
                        headers=headers,
                        json=payload,
                        timeout=self.DEFAULT_TIMEOUT,
                    )

                    if response.status_code >= 500 and attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue

                    if response.status_code != 200:
                        raise APIConnectionError(
                            f"API request failed with status {response.status_code}: {response.text}"
                        )

                    data = response.json()

                    # Some reasoning-capable open models behind Anthropic-compatible routes
                    # emit only "thinking" blocks at low token budgets.
                    # Retry with a larger budget before failing extraction.
                    if provider == "anthropic" and not self._anthropic_has_text_block(data):
                        if attempt < max_retries - 1:
                            current_max_tokens = int(payload.get("max_tokens", self.DEFAULT_MAX_TOKENS))
                            payload["max_tokens"] = min(current_max_tokens * 4, 5000)
                            await asyncio.sleep(2**attempt)
                            continue

                    summary = self._extract_summary(data, provider)

                    lines = summary.split("\n")
                    if len(lines) > max_lines:
                        summary = "\n".join(lines[:max_lines])

                    # Hard cap: 240 chars total (~70 chars × 3 bullets)
                    if len(summary) > 240:
                        truncated = summary[:240]
                        last_newline = truncated.rfind("\n")
                        summary = truncated[:last_newline] if last_newline > 80 else truncated

                    return summary

                except (APIConnectionError, InvalidResponseError):
                    # Don't retry domain-specific errors, raise immediately
                    raise
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise APIConnectionError(f"Request failed: {exc}") from exc
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise SummarizationError(f"Unexpected error: {e}") from e

        raise SummarizationError(f"All {max_retries} retry attempts failed. Last error: {last_error}")

    async def generate_title(self, content: str, max_retries: int = 3) -> str:
        if not content or not content.strip():
            raise SummarizationError("Input content is empty.")

        prompt = self._build_title_prompt(content)
        request_url, headers, payload, provider = self._build_request(prompt)
        payload["max_tokens"] = 80
        last_error = None

        async with async_client_context() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        request_url,
                        headers=headers,
                        json=payload,
                        timeout=self.DEFAULT_TIMEOUT,
                    )
                    if response.status_code >= 500 and attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    if response.status_code != 200:
                        raise APIConnectionError(
                            f"API request failed with status {response.status_code}: {response.text}"
                        )
                    data = response.json()
                    title = self._extract_summary(data, provider)
                    return " ".join(title.split()).strip()[:220]
                except (APIConnectionError, InvalidResponseError):
                    raise
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise APIConnectionError(f"Request failed: {exc}") from exc
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise SummarizationError(f"Unexpected error: {e}") from e

        raise SummarizationError(f"All {max_retries} retry attempts failed. Last error: {last_error}")
