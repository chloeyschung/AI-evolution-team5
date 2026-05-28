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
        extra_headers: dict | None = None,
        timeout: float | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model or self.DEFAULT_MODEL
        provider = provider.strip().lower()
        self.provider = provider if provider in self.PROVIDERS else "auto"
        self.extra_headers = extra_headers or {}
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT

    def _resolved_provider(self) -> str:
        if self.provider != "auto":
            return self.provider

        base = self.base_url.lower()
        if "generativelanguage.googleapis.com" in base or ":generatecontent" in base:
            return "gemini"
        if "/chat/completions" in base or "/v1/responses" in base:
            return "openai"
        # vLLM and other OpenAI-compatible servers commonly expose /v1 as the root path.
        # Anthropic's canonical URL ends with /v1/messages, not bare /v1.
        if base.rstrip("/").endswith("/v1") and "anthropic.com" not in base:
            return "openai"
        return "anthropic"

    def _anthropic_request(self, prompt: str) -> tuple[str, dict[str, str], dict]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "content-type": self.CONTENT_TYPE_JSON,
        }
        headers.update(self.extra_headers)
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
        headers.update(self.extra_headers)
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
        headers.update(self.extra_headers)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": self.DEFAULT_MAX_TOKENS},
        }
        return url, headers, payload

    def _build_request(
        self,
        prompt: str,
        image_bytes: bytes | None = None,
        image_media_type: str = "image/jpeg",
    ) -> tuple[str, dict[str, str], dict, str]:
        provider = self._resolved_provider()
        if provider == "openai":
            url, headers, payload = self._openai_request(prompt)
            if image_bytes is not None:
                import base64
                b64 = base64.b64encode(image_bytes).decode()
                payload["messages"][0]["content"] = [
                    {"type": "image_url", "image_url": {"url": f"data:{image_media_type};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ]
            return url, headers, payload, provider
        if provider == "gemini":
            url, headers, payload = self._gemini_request(prompt)
            return url, headers, payload, provider
        url, headers, payload = self._anthropic_request(prompt)
        return url, headers, payload, "anthropic"

    async def ocr_screenshot(
        self,
        image_bytes: bytes,
        media_type: str = "image/jpeg",
        max_retries: int = 3,
    ) -> tuple[str, str | None]:
        """Extract text and optional URL from a screenshot via the LLM vision endpoint.

        Returns (ocr_text, linked_url_or_None).
        """
        prompt = (
            "Extract all visible text from this screenshot. "
            "If a URL is visible in a browser address bar or anywhere in the image, "
            "output it on the very first line prefixed with 'URL: '. "
            "Then output all other text. "
            "Be thorough — include all readable text."
        )
        request_url, headers, payload, provider = self._build_request(
            prompt, image_bytes=image_bytes, image_media_type=media_type
        )
        payload["max_tokens"] = 600
        last_error = None

        async with async_client_context() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(request_url, headers=headers, json=payload, timeout=self.timeout)
                    if response.status_code >= 500 and attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    if response.status_code != 200:
                        raise APIConnectionError(f"OCR API request failed with status {response.status_code}")
                    data = response.json()
                    raw = self._extract_summary(data, provider)
                    linked_url: str | None = None
                    lines = raw.split("\n")
                    if lines and lines[0].startswith("URL: "):
                        linked_url = lines[0][5:].strip() or None
                        raw = "\n".join(lines[1:]).strip()
                    return raw, linked_url
                except (APIConnectionError, InvalidResponseError):
                    raise
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise APIConnectionError(f"OCR request failed: {exc}") from exc
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise SummarizationError(f"OCR unexpected error: {e}") from e

        raise SummarizationError(f"OCR: all {max_retries} retries failed. Last: {last_error}")

    async def generate_source_narrative(
        self,
        source_name: str,
        kept_titles: list[str],
        topics: list[str],
        manual_context: str | None,
        max_retries: int = 3,
    ) -> str:
        """Generate a consultative prose narrative for a trusted source."""
        titles_block = "\n".join(f"- {t}" for t in kept_titles[:30]) if kept_titles else "(none yet)"
        topics_block = ", ".join(topics[:10]) if topics else "(not classified)"
        manual_block = f"\n\nManual add context: {manual_context}" if manual_context else ""

        prompt = (
            f"Write a short, consultative paragraph (2–4 sentences) explaining why this user "
            f"is drawn to '{source_name}' based on their reading history. "
            f"Tone: personal, insightful — like a thoughtful friend who knows your reading habits. "
            f"Do NOT use structured labels or bullet points — prose only.\n\n"
            f"Kept articles:\n{titles_block}\n\n"
            f"Topics: {topics_block}"
            f"{manual_block}"
        )
        request_url, headers, payload, provider = self._build_request(prompt)
        payload["max_tokens"] = 350
        last_error = None

        async with async_client_context() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(request_url, headers=headers, json=payload, timeout=self.timeout)
                    if response.status_code >= 500 and attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    if response.status_code != 200:
                        raise APIConnectionError(f"Narrative API request failed with status {response.status_code}")
                    data = response.json()
                    return self._extract_summary(data, provider)
                except (APIConnectionError, InvalidResponseError):
                    raise
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise APIConnectionError(f"Narrative request failed: {exc}") from exc
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise SummarizationError(f"Narrative unexpected error: {e}") from e

        raise SummarizationError(f"Narrative: all {max_retries} retries failed. Last: {last_error}")

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
                        timeout=self.timeout,
                    )

                    if response.status_code >= 500 and attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue

                    if response.status_code != 200:
                        raise APIConnectionError(
                            f"API request failed with status {response.status_code}"
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
                        timeout=self.timeout,
                    )
                    if response.status_code >= 500 and attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    if response.status_code != 200:
                        raise APIConnectionError(
                            f"API request failed with status {response.status_code}"
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
