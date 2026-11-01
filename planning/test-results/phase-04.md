# Phase 4 test result — Events and timeline

**Status:** tested

- Replay timeline records include dates, categories, confidence, source-linked evidence IDs, and quote ranges.
- The API returns timeline records in date order and the web UI renders citation buttons.
- A live Peloton run completed all graph stages on 2026-11-01, including Cerebras event extraction. The adapter now selects `CEREBRAS_MODEL` (default `gpt-oss-120b`) because the prior `llama-3.3-70b` model was unavailable to the configured account.

## Limit

The demo fixtures contain concise events rather than ten manually audited events per case. Before a live demo with real filings, perform the planned ten-event hand-check per case.
