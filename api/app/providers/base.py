"""Small provider contracts to keep vendors swappable and testable."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class ProviderError(RuntimeError):
    """A provider failed in a way safe to show as a bounded application error."""


class ProviderUnavailable(ProviderError):
    """An optional integration is unavailable due to configuration or replay mode."""


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    metadata: dict[str, Any]


class DiscoveryProvider(ABC):
    @abstractmethod
    async def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        raise NotImplementedError


class ExtractionProvider(ABC):
    @abstractmethod
    async def extract_events(self, chunks: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError


class ReasoningProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        raise NotImplementedError


class ConversationProvider(ReasoningProvider):
    pass


class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, *, filename: str, language: str = "auto") -> dict[str, Any]:
        raise NotImplementedError


class TextToSpeechProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, *, language: str) -> tuple[bytes, str]:
        """Return audio bytes and MIME type without persisting either."""
        raise NotImplementedError
