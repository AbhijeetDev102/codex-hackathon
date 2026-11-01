# Phase 2 test result — Evidence ingestion

**Status:** tested

- Four CIK-keyed fixture cases load into the database with source, evidence, event, metric, outcome, claim, and report records.
- Evidence IDs such as `E-001` remain stable across events, metrics, claims, the API, and the UI evidence drawer.
- Backend tests confirm a replay run exposes an evidence receipt and source link.
- 2026-11-01: `python -m ruff check app tests` passed and `python -m pytest` passed with 19 tests. The new coverage tests SEC directory matching by company name, ticker, and CIK, plus safe retention of Company Facts when an independent provider has a temporary network failure.
- 2026-11-01: live lookup returned the SEC identity `Tesla, Inc.` (`TSLA`, CIK `1318605`) before research began.
- 2026-11-01: a live Tesla run completed all 11 graph stages with no provider error. It stored 92 disclosed financial records and 11 verified filing-index events. Its outcome remained `unknown`, which is the correct conservative result when the collected evidence does not document a failure outcome.

## Limit

Live SEC/Exa calls require network access and can be rate-limited or temporarily unavailable. Live research preserves evidence from any successful independent source and marks the run `completed_with_limits` when coverage is incomplete.
