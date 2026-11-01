"""Cerebras extraction adapter using its OpenAI-compatible chat endpoint."""

from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import Settings
from .base import ExtractionProvider, ProviderUnavailable
from .cache import RequestCache


class CerebrasProvider(ExtractionProvider):
    def __init__(self, settings: Settings, cache: RequestCache) -> None:
        self.settings = settings
        self.cache = cache

    async def extract_events(self, chunks: list[str]) -> list[dict[str, Any]]:
        if not self.settings.cerebras_api_key:
            raise ProviderUnavailable("Cerebras is not configured. Add CEREBRAS_API_KEY for event extraction.")
        payload = {
            "model": self.settings.cerebras_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Extract dated business events. Return JSON only: {\\\"events\\\": [...]}",
                },
                {"role": "user", "content": "\\n\\n".join(chunks)},
            ],
            "response_format": {"type": "json_object"},
        }

        async def fetch() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.cerebras_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

        result = await self.cache.get_or_fetch("cerebras", payload, fetch)
        content = result["choices"][0]["message"]["content"]
        return list(json.loads(content).get("events", []))
