"""FastAPI dependency factories for configuration and provider adapters."""

from __future__ import annotations

from fastapi import Depends

from .config import Settings, get_settings
from .providers.cache import RequestCache
from .providers.sarvam import SarvamProvider


def get_request_cache(settings: Settings = Depends(get_settings)) -> RequestCache:
    return RequestCache(settings.fixture_path, settings.demo_mode)


def get_sarvam_provider(
    settings: Settings = Depends(get_settings), cache: RequestCache = Depends(get_request_cache)
) -> SarvamProvider:
    return SarvamProvider(settings, cache)
