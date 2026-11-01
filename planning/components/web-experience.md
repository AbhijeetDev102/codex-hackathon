# Web experience

## In simple language

The web app is the visual investigation desk. It lets users choose a company, see what the system is doing, inspect the evidence behind conclusions, and ask follow-up questions without hiding uncertainty.

## Implemented code map

- `/web/app/page.tsx` renders the single-page investigation workflow: live search, saved cases, progress, detailed findings, financial dashboard, outcome, timeline, verification ledger, hypotheses, evidence drawer, report, and assistant.
- `/web/app/globals.css` provides responsive layout, accessible contrast, chart/table styling, print rules, and status states.
- `/web/lib/api.ts` calls REST routes, reads the research WebSocket, reads assistant SSE events, and uses replay data if the API is unavailable.
- `/web/lib/demo-data.ts` supplies safe local fallback data; `/web/lib/types.ts` defines the frontend view models.
- `/web/components/AssistantPanel.tsx` contains the evidence chat and push-to-talk controls.

## Data flow and storage

1. Search calls `/api/companies/search`; live mode searches the SEC company directory by legal name, ticker, or CIK and saves a confirmed match locally. Selecting a searched identity starts a live `/api/research` run. The four bundled cards are deliberately synthetic replay cases: selecting one explicitly requests its matching fixture, while an arbitrary company search remains live.
2. Progress comes from `/ws/research/{run_id}` and is rendered as real node statuses rather than invented percentages.
3. Dashboard sections read the timeline, financial, outcome, inflection, hypothesis, claim, pattern, report, and evidence routes.
4. Clicking a receipt loads its source excerpt in the evidence drawer.
5. The initial demo is an intentionally labelled synthetic replay view. A failed live start or refresh never swaps a selected company into unrelated replay facts: the UI keeps the last valid view and shows a visible live-data error.

The browser does not persist provider keys, source documents, or microphone recordings. It keeps only in-memory view and conversation state for the current page.

## Detailed findings and analysis surfaces

The overview now starts with a **Detailed findings** panel. It deliberately separates four questions a viewer might otherwise blend together:

1. **Documented outcome** says what happened according to the saved record (for example, a bankruptcy filing), shows the system's cautious summary, and exposes the supporting receipts.
2. **Liquidity signal** shows the latest reported cash position and the direction versus the earlier reported period. It is a financial signal, not a claim that cash alone caused the outcome.
3. **Revenue signal** uses the same disclosed metric and period comparison. The card says whether the available series increased, decreased, or does not contain enough periods; it never fills missing values with estimates.
4. **Timeline coverage** states how many verified events are present and the date range they cover. This prevents a sparse timeline from being mistaken for a complete history.

The panel ends with an explicit interpretation limit: the product can show supported contributors and patterns, but public evidence normally cannot prove one exclusive cause of failure. Every factual card includes a clickable receipt when one exists, so the reader can inspect the source wording before relying on it.

The **Verification ledger** appears in Failure analysis. It shows how many candidate claims were checked, how many were supported, how many were removed, and how many verified timeline events exist. It then lists the supported claims with their evidence pills. Unsupported claims are counted but intentionally omitted from the report and from the list of findings. This makes the trust gate visible instead of asking users to trust an invisible model filter.

The responsive layout protects these meanings: four finding cards become two columns on medium screens and two-column ledger statistics remain readable on a phone. The evidence drawer remains the drill-down mechanism; no card treats an unlinked sentence as a researched finding.

## Safe failures and limits

- Network refresh failures preserve the last verified live view and show an error; they do not silently substitute replay data.
- A lost WebSocket is labelled as a polling connection rather than replay mode. The status poll remains active while a run is in progress.
- A WebSocket can report graph completion before the browser has loaded the completed metrics, events, and report. The dashboard therefore performs one final full API refresh after completion and only then stops its polling timer. A completed status can no longer leave the empty startup dashboard visible.
- An unavailable evidence receipt opens an explicit drawer error instead of failing silently. The print action first switches to the final-report view.
- The assistant always exposes citations as clickable receipts. A response without a receipt is presented as a limitation, not a finding.
- Voice controls explain when replay mode or browser permissions prevent voice use; text chat stays available.
- The visual timeline/chart uses fixture data in replay mode. It must not be presented as live company research.
- Built-in bankruptcy and survivor-control cards never silently fall back from an unavailable live SEC endpoint to synthetic data. The browser explicitly requests replay for those labelled demo cards, and changes its connection label to the replay state after the fixture has loaded.
- A live company search can confirm only SEC-reporting companies. A clearly labelled empty result means the current directory search did not identify the requested company; it does not silently show a different demo company.

## Concrete tests

- `web/lib/demo-data.test.ts` verifies saved-case/replay mappings and citation-shaped demo responses.
- `web/lib/api.test.ts` verifies failed live starts/refreshes remain errors rather than replay substitution, and that streamed assistant citations map to visible evidence receipts.
- `api/tests/test_api_replay.py` verifies the exact bundled-card path: short ID `bird` plus CIK `1577967` starts and completes the Bird replay run.
- `npm run test` in `/web` runs the Vitest frontend checks; `npm run build` type-checks and builds the Next.js app.
- Manual live check: search `TSLA`, confirm the Tesla identity and CIK before starting research, then use the Detailed findings receipts and Verification ledger to inspect the run's evidence coverage.
- Manual acceptance checks: search a saved company, simulate a backend outage after a live result, inspect its outcome and timeline, click a receipt during an evidence outage, print from Overview, ask an evidence question, and verify the replay voice fallback message.
