# ADR-007 - Use the SEC ticker directory for live public-company lookup

**Status:** accepted for the prototype

## Context

The original demo picker contained four deliberately bounded replay companies. That was useful for an offline presentation, but it made a live user search for a legitimate public company appear broken or unsupported.

## Decision

In `DEMO_MODE=live`, search the official SEC ticker directory by legal name, ticker, or CIK. Normalize the selected result to legal name, ticker, and CIK, then persist it by CIK before a research run starts. Continue to use the four synthetic fixtures in replay mode.

Live collection treats SEC submissions, SEC Company Facts, and Exa discovery as independent sources. A failure in one source creates a plain-language coverage limit and retains evidence from the other successful sources.

## Consequences

- The prototype can research a broader set of SEC-reporting public companies without adding a separate company-data vendor.
- Results remain bounded by what SEC records and configured optional providers return; this is not support for private companies or every company worldwide.
- A temporary transport problem produces `completed_with_limits` rather than an invented report or the loss of already retrieved facts.
- The SEC directory is fetched via the same provider/cache boundary, keeping replay deterministic and live behavior testable with fixtures.
