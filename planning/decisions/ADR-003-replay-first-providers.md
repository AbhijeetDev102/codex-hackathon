# ADR-003: Replay-first provider design

**Status:** accepted

## Decision

All external provider calls go through narrow adapters and a shared cache/fixture wrapper. `DEMO_MODE=replay` must work without network access for the core research demo.

## Why

Rate limits, API outages, and costs must not break a hackathon demonstration.
