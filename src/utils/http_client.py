"""HTTP client pool for managing async HTTP connections.

This module provides a pooled AsyncClient that reuses connections across
the application instead of creating new clients for each request.

Usage:
    from src.utils.http_client import get_client, async_client_context

    # Option 1: Use the async context manager (recommended for most cases)
    async with async_client_context() as client:
        response = await client.get("https://api.example.com")

    # Option 2: Get the pooled client directly (use your own context management)
    client = get_client()
    # Use client...
    # Note: You are responsible for closing the client when done
"""

from contextlib import asynccontextmanager
from typing import Generator

import httpx


# Default configuration for the pooled client
DEFAULT_TIMEOUT = httpx.Timeout(30.0)
DEFAULT_MAX_CONNECTIONS = 10
DEFAULT_MAX_KEEPALIVE_CONNECTIONS = 10
DEFAULT_LIMIT = httpx.Limits(
    max_connections=DEFAULT_MAX_CONNECTIONS,
    max_keepalive_connections=DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
)


class HttpClientPool:
    """Singleton HTTP client pool that manages connection pooling.

    This class ensures a single AsyncClient instance is used across the
    application with proper connection pooling enabled.
    """

    _instance: httpx.AsyncClient | None = None
    _mounts: dict[str, httpx.AsyncHTTPTransport | httpx.AsyncHTTPTransport] | None = None

    @classmethod
    def get_client(
        cls,
        timeout: httpx.Timeout | None = None,
        follow_redirects: bool = False,
        **kwargs,
    ) -> httpx.AsyncClient:
        """Get the pooled AsyncClient instance.

        If the client has been closed (e.g., at shutdown), this creates
        a new instance.

        Args:
            timeout: Optional timeout to override defaults.
            follow_redirects: Whether to follow redirects automatically.
            **kwargs: Additional kwargs passed to AsyncClient.

        Returns:
            The pooled AsyncClient instance.

        Note:
            The caller is responsible for closing the client when done
            if using this method directly. Prefer using async_client_context()
            for automatic lifecycle management.
        """
        if cls._instance is None or cls._instance.is_closed:
            cls._create_client(timeout, follow_redirects, **kwargs)

        return cls._instance

    @classmethod
    def _create_client(
        cls,
        timeout: httpx.Timeout | None = None,
        follow_redirects: bool = False,
        **kwargs,
    ) -> None:
        """Create a new pooled AsyncClient instance.

        Args:
            timeout: Optional timeout to use.
            follow_redirects: Whether to follow redirects.
            **kwargs: Additional kwargs for AsyncClient.
        """
        cls._instance = httpx.AsyncClient(
            timeout=timeout or DEFAULT_TIMEOUT,
            follow_redirects=follow_redirects,
            limits=DEFAULT_LIMIT,
            **kwargs,
        )

    @classmethod
    async def close(cls) -> None:
        """Close the pooled client and release resources.

        Call this at application shutdown. After closing, get_client()
        will create a new instance on next call.
        """
        if cls._instance and not cls._instance.is_closed:
            await cls._instance.aclose()
            cls._instance = None

    @classmethod
    async def close_client(cls, client: httpx.AsyncClient) -> None:
        """Close a specific client if it matches the pooled instance.

        Args:
            client: The client to close.
        """
        if cls._instance is client and not client.is_closed:
            await client.aclose()
            cls._instance = None


# Convenience function to get the pooled client
get_pooled_client = HttpClientPool.get_client


@asynccontextmanager
async def async_client_context(
    timeout: httpx.Timeout | None = None,
    follow_redirects: bool = False,
    **kwargs,
) -> Generator[httpx.AsyncClient, None, None]:
    """Context manager for the pooled HTTP client.

    This is the recommended way to use the client pool. It ensures
    proper resource management and connection reuse.

    Args:
        timeout: Optional timeout to use.
        follow_redirects: Whether to follow redirects.
        **kwargs: Additional kwargs for AsyncClient.

    Yields:
        An AsyncClient instance from the pool.

    Example:
        async with async_client_context() as client:
            response = await client.get("https://api.example.com")
    """
    client = get_pooled_client(timeout, follow_redirects, **kwargs)
    try:
        yield client
    finally:
        # Don't close the client - keep it in the pool for reuse
        # The pool is closed at application shutdown via close()
        pass


def shutdown_http_pool() -> None:
    """Schedule HTTP pool shutdown for application exit.

    This can be called at application startup to ensure cleanup on exit.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            return
        loop.add_finalizer(HttpClientPool.close)
    except Exception:
        pass
