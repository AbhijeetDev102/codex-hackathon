# Phase 6 — Product UI and progress

**Status:** tested

## Goal

Make the research process understandable without hiding uncertainty.

## Scope

- Company selection, real graph progress, detailed findings, financial chart, outcome, timeline, verification ledger, hypothesis cards, evidence drawer, report, and print view.
- Use a WebSocket for real node state; never present invented percentages.
- Make citations clickable and preserve the disclosed/derived distinction in charts.

## Gate

Browser tests complete a replay run. A manual reviewer can click a displayed claim and see its highlighted supporting quote.

## Implementation record

- Code: `/web/app/page.tsx`, `/web/components/AssistantPanel.tsx`, and `/web/lib/api.ts`.
- Inputs: API/replay response records. Outputs: dashboard views, status progress, evidence drawer, printable report, and accessible controls.
- Tests: TypeScript, Vitest, and Next production build pass. The API mapper converts raw USD into displayed millions, retains all claim-verification records for the ledger, and fetches source evidence on demand.
- 2026-11-01 update: live search prompts for a U.S. company, ticker, or CIK; the Detailed findings panel distinguishes outcome, liquidity, revenue, and timeline coverage; and the Verification ledger makes supported and removed claims visible with linked receipts.
- 2026-11-01 runtime fix: live progress can reach `completed` through the WebSocket before the browser has fetched the final result records. The refresh loop now loads the completed run before stopping, preventing a completed-but-empty dashboard.
- 2026-11-01 demo/live fix: built-in cards explicitly request their cited synthetic fixtures even when the app is globally in live mode. This prevents a known demo company with no SEC Company Facts endpoint from producing an empty live dashboard; arbitrary searches continue to request live research.
- Audit remediation: failed live starts/refreshes preserve the last valid state with a visible error; WebSocket loss becomes polling status; evidence-load errors are visible; and Print report switches to the report view before invoking browser print.
