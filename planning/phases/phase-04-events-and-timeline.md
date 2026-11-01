# Phase 4 — Events and timeline

**Status:** tested

## Goal

Create a trustworthy event timeline from evidence chunks.

## Scope

- Cerebras structured extraction behind an adapter, with replay and rule-based fallback.
- Pydantic validation, date normalization, quote matching, source checks, and duplicate removal.
- Timeline endpoints and explicit confidence/date precision fields.

## Gate

Hand-check ten events for date, quote, original source, and evidence ID. Invalid model output must be rejected instead of silently repaired into facts.

## Implementation record

- Code: `/api/app/providers/cerebras.py`, `/api/app/services/replay.py`, and `/api/app/routes/research.py`.
- Inputs: source chunks. Outputs: normalized events with date, category, confidence, and evidence IDs.
- Tests: replay timeline records render through the API and UI. A live structured Cerebras extraction passed on 2026-11-01 after selecting an account-available model; the planned manual ten-event audit remains outstanding.
