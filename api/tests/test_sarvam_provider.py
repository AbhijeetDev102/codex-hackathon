"""Contract tests for the raw Sarvam model adapter.

These tests use a local HTTP double: they prove the payload we send to Sarvam
matches the documented model endpoints without requiring a key or real audio.
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import ClassVar, Self
from unittest.mock import patch

import httpx

from app.config import Settings
from app.providers.cache import RequestCache
from app.providers.sarvam import SarvamProvider


class RecordingAsyncClient:
    """Minimal async ``httpx.AsyncClient`` replacement used by adapter tests."""

    calls: ClassVar[list[tuple[str, dict[str, object]]]] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        del args

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        self.calls.append((url, dict(kwargs)))
        request = httpx.Request("POST", url)
        if url.endswith("/speech-to-text"):
            return httpx.Response(
                200,
                request=request,
                json={"transcript": "नमस्ते WeWork", "language_code": "hi-IN"},
            )
        return httpx.Response(
            200,
            request=request,
            json={"audios": [base64.b64encode(b"RIFFdemo").decode()]},
        )


def _provider(tmp_path: Path) -> SarvamProvider:
    settings = Settings(
        database_url="sqlite:///:memory:",
        demo_mode="live",
        sarvam_api_key="test-key",
        sarvam_stt_model="saaras:v4",
        sarvam_tts_model="bulbul:v4-flash",
        sarvam_tts_speaker=None,
    )
    return SarvamProvider(settings, RequestCache(tmp_path))


def test_sarvam_voice_payloads_use_current_saaras_and_bulbul_contracts(tmp_path: Path) -> None:
    RecordingAsyncClient.calls = []
    provider = _provider(tmp_path)

    with patch("app.providers.sarvam.httpx.AsyncClient", RecordingAsyncClient):
        transcript = asyncio.run(provider.transcribe(b"fake wav", filename="question.wav"))
        audio, media_type = asyncio.run(provider.synthesize("Verified answer [E-001]", language="hi"))

    stt_url, stt_request = RecordingAsyncClient.calls[0]
    assert stt_url.endswith("/speech-to-text")
    assert stt_request["data"] == {
        "model": "saaras:v4",
        "mode": "transcribe",
        "language_code": "auto",
    }
    assert stt_request["files"] == {"file": ("question.wav", b"fake wav", "audio/wav")}
    assert transcript == {"text": "नमस्ते WeWork", "language": "hi-IN"}

    tts_url, tts_request = RecordingAsyncClient.calls[1]
    assert tts_url.endswith("/text-to-speech")
    assert tts_request["json"] == {
        "text": "Verified answer [E-001]",
        "language_code": "hi-IN",
        "model": "bulbul:v4-flash",
        "output_audio_codec": "wav",
        "speech_sample_rate": 16_000,
    }
    assert audio == b"RIFFdemo"
    assert media_type == "audio/wav"
