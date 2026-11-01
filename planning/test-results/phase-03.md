# Phase 3 test result — Deterministic analysis

**Status:** tested

- Unit tests cover derived cash burn, quarter-over-quarter calculations, conservative bankruptcy/distress outcome rules, and robust-MAD inflection detection.
- Financial values remain explicitly marked `disclosed` or `derived`.
- The outcome classifier returns `distress_without_failure` for the Carvana control when no supported failure event exists.
- A graph regression test verifies that a distress-without-failure outcome preserves the cash/loss `E-...` receipts that support the label.
