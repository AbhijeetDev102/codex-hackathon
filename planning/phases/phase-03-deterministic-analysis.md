# Phase 3 — Deterministic analysis

**Status:** tested

## Goal

Calculate facts before asking an AI to explain them.

## Scope

- Derive revenue, cash, net loss, and operating-cash-flow metrics from XBRL.
- Clearly label filing disclosures separately from calculated values.
- Add evidence-linked outcome assessment: bankruptcy, delisted, wound down, going concern, distress without failure, or unknown.
- Detect potential inflections using rolling MAD with a qualitative fallback for sparse histories.

## Gate

Hand-check five financial values against filings and review the outcome plus two or three turning points for one case.

## Implementation record

- Code: `/api/app/analysis/metrics.py`, `outcomes.py`, and `inflections.py`.
- Inputs: filing/XBRL metrics and verified events. Outputs: derived metrics, conservative outcome labels, and non-causal turning-point candidates.
- Tests: unit coverage verifies cash burn, quarter changes, outcome priority, robust-MAD calculation, and financial receipts on a distress-without-failure result. Real-filing hand checks remain a demo-day task.
