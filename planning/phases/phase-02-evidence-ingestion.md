# Phase 2 — Evidence ingestion

**Status:** tested

## Goal

Collect public company material and store it so every later statement can be traced to a source.

## Scope

- Company search and confirmation through the official SEC ticker directory in live mode, with known demo-company CIK fallbacks in replay mode.
- SEC submissions, filings, XBRL facts, and optional Exa discovery through provider adapters.
- Source storage, deterministic chunking, content hashes, per-run `E-001` evidence labels, and request caching.
- Record/replay fixtures for every external call.

## Gate

One selected company collects and replays successfully. A reviewer can follow each saved quote to its exact source and evidence ID.

## Implementation record

- Code: `/api/app/providers/`, `/api/app/services/replay.py`, `/api/app/services/repository.py`, `/api/app/graph/runner.py`, and `/fixtures/demo_cases.json`.
- Inputs: confirmed company CIK plus SEC/Exa responses or replay fixture. Outputs: sources, evidence receipts, events, and metrics.
- Tests: all four fixtures load and the evidence endpoint returns the selected source/quote record. SEC name/ticker/CIK matching and partial-provider evidence retention are covered without calling the network.
- 2026-11-01 update: the SEC submissions index, Company Facts, and Exa discovery are handled independently. A transient failure now preserves data from the successful sources and marks the coverage limitation rather than failing the entire collection stage.
