"""OpenAI reasoning adapter used by graph nodes, never directly by routes."""

from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings
from .base import ProviderResponse, ProviderUnavailable, ReasoningProvider
from .cache import RequestCache


class OpenAIProvider(ReasoningProvider):
    def __init__(self, settings: Settings, cache: RequestCache) -> None:
        self.settings = settings
        self.cache = cache

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        if not self.settings.openai_api_key:
            raise ProviderUnavailable("OpenAI is not configured. Add OPENAI_API_KEY for live reasoning.")
        payload = {"model": kwargs.pop("model", "gpt-4.1-mini"), "messages": messages, **kwargs}

        async def fetch() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

        result = await self.cache.get_or_fetch("openai", payload, fetch)
        choice = result["choices"][0]
        return ProviderResponse(content=choice["message"]["content"], metadata={"usage": result.get("usage", {})})
