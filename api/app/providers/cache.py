"""Deterministic file cache for recording and replaying external API calls."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .base import ProviderUnavailable


class RequestCache:
    """Caches JSON-compatible results by a stable hash of a sanitized request payload."""

    def __init__(self, root: Path, mode: str = "live") -> None:
        self.root = root
        self.mode = mode.lower()

    @staticmethod
    def key(namespace: str, payload: dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"{namespace}-{digest}"

    def _path(self, namespace: str, payload: dict[str, Any]) -> Path:
        return self.root / namespace / f"{self.key(namespace, payload)}.json"

    async def get_or_fetch(
        self,
        namespace: str,
        payload: dict[str, Any],
        fetch: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        path = self._path(namespace, payload)
        if self.mode == "replay":
            if not path.exists():
                raise ProviderUnavailable(
                    f"No replay fixture for {namespace}. Use a saved demo case or run in live mode."
                )
            return json.loads(path.read_text(encoding="utf-8"))

        result = await fetch()
        if self.mode == "record":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return result
