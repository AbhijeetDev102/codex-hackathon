# Phase 7 test result — Patterns and resilience

**Status:** tested

- Fixtures cover three failure cases and the Carvana survivor control.
- Backend tests verify all four outcomes and confirm Carvana remains `distress_without_failure`.
- The repository includes eight archetypes and twelve comparison-case notes.
- Deterministic local matching now reads both data sets, returns up to two comparable cases with explicit similarities/differences, and persists the `pattern_match` object into the final report used by `GET /patterns`.
- Graph tests cover comparable-case output and report persistence; the replay API test verifies the public patterns endpoint returns two cases.
- Browser print styling is included; full offline Compose rehearsal awaits Docker Desktop.
