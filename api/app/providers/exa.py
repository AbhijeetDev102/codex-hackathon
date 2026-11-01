"""Exa discovery adapter. It remains optional in replay mode and without credentials."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..config import Settings
from .base import DiscoveryProvider, ProviderUnavailable
from .cache import RequestCache


class ExaProvider(DiscoveryProvider):
    def __init__(self, settings: Settings, cache: RequestCache) -> None:
        self.settings = settings
        self.cache = cache

    async def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        if not self.settings.exa_api_key:
            raise ProviderUnavailable("Exa is not configured. Add EXA_API_KEY to enable live discovery.")

        payload = {"query": query, "numResults": limit, "contents": {"text": True}}

        async def fetch() -> dict[str, Any]:
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            "https://api.exa.ai/search",
                            headers={"x-api-key": self.settings.exa_api_key},
                            json=payload,
                        )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as error:
                    raise ProviderUnavailable(f"Exa request failed: {error.response.status_code}") from error
                except httpx.RequestError as error:
                    if attempt == 2:
                        raise ProviderUnavailable("Exa could not be reached after three attempts.") from error
                    await asyncio.sleep(0.25 * (attempt + 1))
            raise ProviderUnavailable("Exa did not return a response.")

        result = await self.cache.get_or_fetch("exa", payload, fetch)
        return list(result.get("results", []))
