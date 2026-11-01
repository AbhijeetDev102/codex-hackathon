# Phase 6 test result — Product UI

**Status:** tested

- `npm.cmd run typecheck` passed.
- `npm.cmd run test` passed.
- `npm.cmd run build` passed.
- The API adapter now maps live/replay API records into dashboard models, including units, node status, citations, and evidence drawer lookup.
- 2026-11-01 audit remediation: `web/lib/api.test.ts` adds regression coverage for no live-to-replay substitution and cited assistant SSE mapping. The suite now has 5 passing frontend tests.
- 2026-11-01 runtime remediation: a Bird card click initially sent the stable frontend ID `bird`, while the database used a UUID. The API now resolves the supplied CIK fallback; the exact request completed successfully in Docker replay mode. Backend suite: 17 passing tests.
- 2026-11-01 UI expansion: the overview now includes a four-part Detailed findings panel (outcome, liquidity, revenue, and timeline coverage) with evidence receipts, while Failure analysis includes a Verification ledger for checked, supported, and removed claims. `npm.cmd run typecheck` and `npm.cmd run test` passed with 5 frontend tests before container deployment.
- 2026-11-01 deployed check: the local web application responded at `http://localhost:3000` and its overview rendered the Detailed findings surface. The companion Verification ledger is rendered when the user opens Failure analysis.
- 2026-11-01 defect diagnosis: Good Times Restaurants (`GTIM`) displayed a completed graph with zero visible records because the WebSocket state update stopped browser polling before the final API data load. Database inspection confirmed its completed run had 95 metrics and 38 verified events. The polling logic now fetches the final run payload before stopping. `npm.cmd run typecheck`, `npm.cmd run test` (5 tests), and `npm.cmd run build` passed before redeployment.
- 2026-11-01 fixture/live regression: WeWork's SEC Company Facts URL returns HTTP 404, so forcing the built-in WeWork card through live collection produces no financial records. The card now explicitly requests its labelled fixture while ordinary company lookup remains live. Backend checks passed (19 tests); frontend type-check and production build passed; Vitest now has 6 passing tests, including the explicit fixture request contract.
- Browser follow-up: manually verify print-from-Overview switches to Final report, evidence-service error drawer, and WebSocket disconnect/polling label against a running stack.
