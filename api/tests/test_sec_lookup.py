import pytest

from app.graph.runner import _collect_live
from app.providers.sec import filter_ticker_catalog


def test_sec_ticker_catalog_matches_name_ticker_and_cik_without_network() -> None:
    catalog = [
        {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
    ]

    assert filter_ticker_catalog(catalog, "tesla") == [
        {"legal_name": "Tesla, Inc.", "ticker": "TSLA", "cik": "1318605"}
    ]
    assert filter_ticker_catalog(catalog, "AAPL")[0]["legal_name"] == "Apple Inc."
    assert filter_ticker_catalog(catalog, "320193")[0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_live_collection_keeps_available_sec_evidence_when_a_provider_fails() -> None:
    class PartlyAvailableSec:
        async def submissions(self, cik: str) -> dict[str, object]:
            raise OSError("temporary name-resolution failure")

        async def company_facts(self, cik: str) -> dict[str, object]:
            return {
                "facts": {
                    "us-gaap": {
                        "Revenues": {
                            "units": {
                                "USD": [
                                    {
                                        "form": "10-K",
                                        "end": "2025-12-31",
                                        "fy": 2025,
                                        "fp": "FY",
                                        "val": 1250000,
                                        "accn": "0000000000-25-000001",
                                        "primaryDocument": "annual.htm",
                                    }
                                ]
                            }
                        }
                    }
                }
            }

    class UnavailableDiscovery:
        async def search(self, query: str, *, limit: int = 10) -> list[dict[str, object]]:
            raise OSError("temporary name-resolution failure")

    result = await _collect_live(
        {"company": {"cik": "1318605", "legal_name": "Tesla, Inc."}},
        PartlyAvailableSec(),  # type: ignore[arg-type]
        UnavailableDiscovery(),  # type: ignore[arg-type]
    )

    assert result["metrics"]
    assert result["evidence"]
    assert result["events"] == []
    assert result["errors"] == [
        "SEC filing-index data was temporarily unavailable; filing timeline coverage is limited.",
        "Supplementary public-reporting discovery was unavailable; SEC evidence was retained.",
    ]
