# Phase 7 — Patterns and demo resilience

**Status:** tested

## Goal

Add useful comparisons while making the demo dependable without the internet.

## Scope

- Store archetypes and curated historical cases for deterministic local matching. Embeddings remain a scale-up follow-up, not a claim of the current prototype.
- Explain both similarities and differences; permit “no good match.”
- Complete fixtures for three failures and one survivor, offline replay, cost/time display, and demo rehearsal checklist.

## Gate

All four cases work in replay with networking disabled. The survivor is not presented as a failure, and the printable report works.

## Implementation record

- Code/data: `/knowledge/archetypes.json`, `/knowledge/cases.json`, `/fixtures/demo_cases.json`, and graph pattern matching.
- Inputs: verified hypotheses/events and local archetype signals. Outputs: one explicit archetype, its matching signals, and up to two comparable cases with differences to check; a report/API consumer sees the same `pattern_match` object.
- Tests: four fixture outcomes pass; Carvana is retained as `distress_without_failure`; graph/API tests assert pattern results contain two comparables. Full offline Compose rehearsal awaits Docker Desktop.
