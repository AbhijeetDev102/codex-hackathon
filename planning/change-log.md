# Change log

## Unreleased

- 2026-11-01 - Separated built-in demonstration cards from arbitrary live lookup. The four labelled synthetic cases now explicitly load their matching replay fixtures even while `DEMO_MODE=live`; searched SEC-reporting companies continue to run live. This resolves the empty WeWork view caused by the SEC Company Facts endpoint returning 404 for its CIK. See [web experience](components/web-experience.md) and [Phase 6 results](test-results/phase-06.md).

- 2026-11-01 - Fixed the live dashboard completion race: WebSocket progress could mark a run complete before metrics, events, and report records were fetched, leaving a misleading empty view. The browser now completes one final data refresh before it stops polling. Verified against a Good Times Restaurants run containing 95 metrics and 38 events. See [web experience](components/web-experience.md) and [Phase 6 results](test-results/phase-06.md).

- 2026-11-01 - Expanded live-company discovery beyond the four replay cards: SEC directory search now accepts legal name, ticker, and CIK and stores confirmed public-company identities by CIK. Collection keeps usable SEC evidence when a separate SEC endpoint or supplementary discovery is temporarily unavailable, and records a clear coverage limit. Added detailed findings and a visible verification ledger to the UI. See [evidence pipeline](components/evidence-pipeline.md), [web experience](components/web-experience.md), [ADR-007](decisions/ADR-007-sec-public-company-lookup.md), [Phase 2 results](test-results/phase-02.md), and [Phase 6 results](test-results/phase-06.md).

### Planning baseline

- Renamed `architechture.md` to `architecture.md` and corrected references.
- Reconciled the missing `assess_outcome` graph node, state, API, data model, and UI requirement.
- Added the evidence-grounded Sarvam chat and push-to-talk voice design.
- Added phase, component, decision, and test-evidence documentation conventions.

### Implementation â€” 2026-11-01

- Implemented the FastAPI, database, provider, replay, deterministic-analysis, LangGraph, and Sarvam-assistant layers. See [platform](components/platform.md), [analysis](components/analysis-and-outcomes.md), [research graph](components/research-graph-and-trust.md), and [assistant](components/sarvam-assistant.md).
- Implemented the Next.js dashboard, evidence drawer, printable report, API mapper, chat, and push-to-talk controls. See [web experience](components/web-experience.md).
- Added four replay fixtures, eight archetypes, twelve comparison notes, Docker Compose, root run instructions, and automated backend/frontend checks.
- Recorded the local Docker Desktop limitation and live-provider validation work in [Phase 10 results](test-results/phase-10.md).
- Aligned the live Sarvam adapter with the current Saaras v4 and Bulbul v4 Flash REST request contracts, then added a non-network regression test for those payloads. See [assistant](components/sarvam-assistant.md) and [Phase 9 results](test-results/phase-09.md).
- 2026-11-01, Phase 7: preserved live `E-...` metric receipts through inflection detection and made deterministic local pattern matches reportable. Matches now use both archetype and comparison-case knowledge, return up to two comparable cases with similarities/differences, and persist in the final report/API. See [analysis](components/analysis-and-outcomes.md), [research graph](components/research-graph-and-trust.md), and [Phase 7 results](test-results/phase-07.md).
- 2026-11-01 â€” Hardened the web experience after a Phase 6/9 audit: live errors retain the last verified data, WebSocket loss reports polling, print targets the report, evidence failures are visible, and microphone streams are cleaned up on navigation. Added frontend adapter regression tests. See [web experience](components/web-experience.md), [Phase 6 results](test-results/phase-06.md), and [Phase 9 results](test-results/phase-09.md).

- 2026-11-01 — Hardened the Phase 8 assistant trust gate so every substantive Sarvam response sentence needs an approved run receipt; invalid, unknown, or incomplete citations are replaced before storage. See [assistant](components/sarvam-assistant.md) and [Phase 8 results](test-results/phase-08.md).
- 2026-11-01 — Made clean local/container setup more reliable: API package discovery excludes runtime data, web Docker builds use the lockfile and a focused build context, and Compose accepts optional live-provider settings from `.env`. See [platform](components/platform.md) and [Phase 1 results](test-results/phase-01.md).
- 2026-11-01 — Clarified `architecture.md` to distinguish shipped replay-first behavior from planned scale-up infrastructure. See [implementation status](implementation-status.md).
- 2026-11-01 — Preserved financial evidence receipts on `distress_without_failure` outcomes, so every supported non-failure assessment remains traceable. See [analysis](components/analysis-and-outcomes.md) and [Phase 3 results](test-results/phase-03.md).

- 2026-11-01 - Ran the full Docker stack, replay companies, a live Peloton research run, and minimal configured-provider probes. Replaced the unavailable hard-coded Cerebras model with configurable `CEREBRAS_MODEL` (default `gpt-oss-120b`). See [platform](components/platform.md), [evidence pipeline](components/evidence-pipeline.md), and [Phase 10 results](test-results/phase-10.md).
- 2026-11-01 - Isolated Sarvam tests from real `.env` keys and speaker choices, then re-ran the backend suite with all 16 tests passing. See [assistant](components/sarvam-assistant.md) and [Phase 9 results](test-results/phase-09.md).
- 2026-11-01 - Fixed bundled replay-company cards failing against UUID-backed database rows. `/api/research` now uses the sent public CIK when the short card ID is not a database ID; Bird was verified end to end in Docker. See [web experience](components/web-experience.md) and [Phase 6 results](test-results/phase-06.md).

Future entries must state the date, affected phase, user-visible effect, and links to the relevant component and test record.
