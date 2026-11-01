"""Sarvam raw-model adapter for grounded conversation and transient speech processing."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from ..config import Settings
from .base import (
    ConversationProvider,
    ProviderError,
    ProviderResponse,
    ProviderUnavailable,
    SpeechToTextProvider,
    TextToSpeechProvider,
)
from .cache import RequestCache


class SarvamProvider(ConversationProvider, SpeechToTextProvider, TextToSpeechProvider):
    """Use Sarvam's model APIs, not managed Voice Agents, to retain evidence controls.

    Audio is deliberately not passed through ``RequestCache``: user recordings and
    generated reply audio are transient by product policy.
    """

    def __init__(self, settings: Settings, cache: RequestCache) -> None:
        self.settings = settings
        self.cache = cache

    @property
    def _headers(self) -> dict[str, str]:
        if not self.settings.sarvam_api_key:
            raise ProviderUnavailable("Sarvam is not configured. Add SARVAM_API_KEY to enable assistant voice.")
        return {"api-subscription-key": self.settings.sarvam_api_key}

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        payload = {
            "model": kwargs.pop("model", self.settings.sarvam_chat_model),
            "messages": messages,
            "stream": False,
            **kwargs,
        }

        async def fetch() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.settings.sarvam_base_url.rstrip('/')}/v1/chat/completions",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json=payload,
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    raise ProviderError(f"Sarvam chat failed: {error.response.status_code}") from error
                return response.json()

        result = await self.cache.get_or_fetch("sarvam-chat", payload, fetch)
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        if not content:
            raise ProviderError("Sarvam returned an empty chat response.")
        return ProviderResponse(content=content, metadata={"usage": result.get("usage", {})})

    async def transcribe(self, audio: bytes, *, filename: str, language: str = "auto") -> dict[str, Any]:
        if self.settings.is_replay:
            raise ProviderUnavailable("Voice transcription is unavailable in replay mode. Type your question instead.")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.settings.sarvam_base_url.rstrip('/')}/speech-to-text",
                headers=self._headers,
                data={
                    "model": self.settings.sarvam_stt_model,
                    "mode": "transcribe",
                    # Let Saaras identify English, Hindi, or a mixed-language turn.
                    "language_code": language or "auto",
                },
                files={"file": (filename, audio, "audio/wav")},
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise ProviderError(f"Sarvam transcription failed: {error.response.status_code}") from error
            result = response.json()
        text = result.get("transcript") or result.get("text")
        if not text:
            raise ProviderError("Sarvam returned no transcript.")
        return {"text": text, "language": result.get("language_code") or language}

    async def synthesize(self, text: str, *, language: str) -> tuple[bytes, str]:
        if self.settings.is_replay:
            raise ProviderUnavailable("Voice playback is unavailable in replay mode. Read the cited answer on screen.")
        language_code = {"en": "en-IN", "hi": "hi-IN"}.get(language, "hi-IN")
        payload: dict[str, Any] = {
            # This is Sarvam's REST TTS schema for Bulbul v4 Flash.
            "text": text[:2500],
            "language_code": language_code,
            "model": self.settings.sarvam_tts_model,
            "output_audio_codec": "wav",
            "speech_sample_rate": 16_000,
        }
        if self.settings.sarvam_tts_speaker:
            payload["speaker"] = self.settings.sarvam_tts_speaker
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.settings.sarvam_base_url.rstrip('/')}/text-to-speech",
                headers={**self._headers, "Content-Type": "application/json"},
                json=payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise ProviderError(f"Sarvam speech synthesis failed: {error.response.status_code}") from error
            result = response.json()
        audio_value = (result.get("audios") or result.get("audio") or [None])[0]
        if not audio_value:
            raise ProviderError("Sarvam returned no speech audio.")
        if isinstance(audio_value, str) and audio_value.startswith("data:"):
            mime_type, encoded = audio_value.split(",", 1)
            return base64.b64decode(encoded), mime_type.split(";", 1)[0].removeprefix("data:")
        if isinstance(audio_value, str):
            return base64.b64decode(audio_value), "audio/wav"
        raise ProviderError("Sarvam returned speech in an unsupported format.")
