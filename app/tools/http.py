"""Shared HTTP client construction for agent tools."""

import httpx


def get_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """Return an HTTP client with the tools' standard ten-second timeout."""
    return httpx.Client(timeout=10, transport=transport)
