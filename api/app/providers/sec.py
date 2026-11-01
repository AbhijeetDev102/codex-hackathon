"""SEC EDGAR adapter with descriptive User-Agent and replay support."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..config import Settings
from .base import DiscoveryProvider, ProviderError
from .cache import RequestCache

DEMO_COMPANIES: tuple[dict[str, str], ...] = (
    {"legal_name": "WeWork Inc.", "cik": "1533523", "ticker": "WE"},
    {"legal_name": "Bed Bath & Beyond Inc.", "cik": "886158", "ticker": "BBBY"},
    {"legal_name": "Bird Global, Inc.", "cik": "1577967", "ticker": "BRDS"},
    {"legal_name": "Carvana Co.", "cik": "1690820", "ticker": "CVNA"},
    {"legal_name": "Peloton Interactive, Inc.", "cik": "1639825", "ticker": "PTON"},
)

# SEC's company-ticker directory changes far less frequently than a user types.
# Keep it only in process memory: it contains public identity data and no keys.
_ticker_catalog: list[dict[str, str]] | None = None


def filter_ticker_catalog(
    catalog: list[dict[str, Any]], query: str, *, limit: int = 10
) -> list[dict[str, str]]:
    """Return CIK-confirmed public-company identities matching name, ticker, or CIK."""

    normalized = query.casefold().strip()
    matches: list[dict[str, str]] = []
    for item in catalog:
        legal_name = str(item.get("title") or item.get("legal_name") or "").strip()
        ticker = str(item.get("ticker") or "").strip().upper()
        cik_value = item.get("cik_str", item.get("cik"))
        try:
            cik = str(int(str(cik_value)))
        except (TypeError, ValueError):
            continue
        searchable = (legal_name.casefold(), ticker.casefold(), cik)
        if not legal_name or not any(normalized in value for value in searchable):
            continue
        matches.append({"legal_name": legal_name, "ticker": ticker, "cik": cik})

    def rank(item: dict[str, str]) -> tuple[int, str]:
        exact = normalized in {item["ticker"].casefold(), item["cik"], item["legal_name"].casefold()}
        prefix = item["legal_name"].casefold().startswith(normalized)
        return (0 if exact else 1 if prefix else 2, item["legal_name"])

    return sorted(matches, key=rank)[:limit]


class SecProvider(DiscoveryProvider):
    def __init__(self, settings: Settings, cache: RequestCache) -> None:
        self.settings = settings
        self.cache = cache

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": self.settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}

    async def _get_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async def fetch() -> dict[str, Any]:
            url = f"{self.settings.sec_base_url.rstrip('/')}{path}"
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                        response = await client.get(url)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as error:
                    raise ProviderError(f"SEC request failed: {error.response.status_code}") from error
                except httpx.RequestError as error:
                    if attempt == 2:
                        raise ProviderError("SEC request could not reach the provider after three attempts.") from error
                    await asyncio.sleep(0.25 * (attempt + 1))
            raise ProviderError("SEC request did not return a response.")

        return await self.cache.get_or_fetch("sec", {"path": path, **payload}, fetch)

    async def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        normalized = query.casefold().strip()
        demo_matches = [
            company
            for company in DEMO_COMPANIES
            if normalized in company["legal_name"].casefold()
            or normalized in company["ticker"].casefold()
            or normalized in company["cik"]
        ][:limit]
        if self.settings.is_replay:
            return demo_matches

        global _ticker_catalog
        if _ticker_catalog is None:
            payload: dict[str, Any] | list[Any] | None = None
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=30.0, headers=self.headers) as client:
                        response = await client.get(self.settings.sec_ticker_directory_url)
                    response.raise_for_status()
                    payload = response.json()
                    break
                except httpx.HTTPStatusError as error:
                    raise ProviderError(f"SEC company lookup failed: {error.response.status_code}") from error
                except httpx.RequestError as error:
                    if attempt == 2:
                        raise ProviderError("SEC company lookup could not reach the provider after three attempts.") from error
                    await asyncio.sleep(0.25 * (attempt + 1))
            rows = list(payload.values()) if isinstance(payload, dict) else []
            _ticker_catalog = [dict(row) for row in rows if isinstance(row, dict)]
        matches = filter_ticker_catalog(_ticker_catalog, query, limit=limit)
        # The saved demo identities remain useful if SEC's directory is temporarily incomplete.
        return matches or demo_matches

    async def submissions(self, cik: str) -> dict[str, Any]:
        return await self._get_json(f"/submissions/CIK{int(cik):010d}.json", {"cik": cik})

    async def company_facts(self, cik: str) -> dict[str, Any]:
        return await self._get_json(f"/api/xbrl/companyfacts/CIK{int(cik):010d}.json", {"cik": cik})
