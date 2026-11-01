# Phase 5 — Graph and verification

**Status:** tested

## Goal

Use a bounded LangGraph workflow to produce explanations without allowing unsupported statements into reports.

## Scope

- Wire collection, event extraction, financials, outcome, inflections, hypotheses, critic, verification, patterns, and report nodes.
- Require atomic claim/evidence links from hypothesis creation onward.
- Run quote, date, math, and support checks; remove unsupported claims.
- Cap retries, provider calls, token budget, and critic revisions; implement `completed_with_limits`.

## Gate

A replay run completes, reports show the correct verification score, unsupported claims are absent, and the graph cannot revise more than twice.

## Implementation record

- Code: `/api/app/graph/`, `/api/app/analysis/verification.py`, and `/api/app/graph/runner.py`.
- Inputs: collected evidence, events, metrics, and model-proposed claims. Outputs: approved claims, rejected-claim audit data, verification counts, patterns, and a report.
- Tests: a pinned LangGraph graph rejects uncited claims, excludes them from the report, and has a bounded revision route.
