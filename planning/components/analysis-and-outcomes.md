# Financial analysis, inflections, and outcomes

## In simple language

This component converts verified filing numbers into labelled chart data, highlights unusually large changes, and says what happened to the company without pretending to prove why it happened.

## Implemented code map

- `/api/app/analysis/metrics.py` defines `MetricPoint`, derives cash burn from negative operating cash flow, and calculates quarter-over-quarter changes. Derived values remain marked `derived`.
- `/api/app/analysis/inflections.py` finds robust change candidates from a historical baseline and states that timing is not proof of cause.
- `/api/app/analysis/outcomes.py` classifies verified evidence as bankruptcy, delisted, wound down, going concern, distress without failure, or unknown.
- `/api/app/graph/nodes.py` applies these deterministic functions inside the graph.
- `/api/app/models.py` stores `metrics`, `inflections`, and `outcomes`; `/api/app/routes/research.py` returns them through the financial, inflection, and outcome endpoints.

## Data flow and storage

1. SEC Company Facts or replay fixtures provide disclosed revenue, cash, net loss, and operating-cash-flow values with evidence keys.
2. The metrics functions add transparent derived values; they never replace the disclosed source value. Both live `evidence_key` and persisted `evidence_id` receipts are carried into derived metrics and inflections.
3. Inflection detection compares changes with the earlier series and returns an explanation plus relevant receipts.
4. Outcome rules look for verified bankruptcy, delisting, wind-down, or going-concern language. If the evidence only shows stress, the outcome stays `distress_without_failure` and carries the supporting cash/loss receipts; an `unknown` result clearly signals no supported outcome conclusion.

## Safe failures and limits

- Missing or too-short metric series produces no fabricated turning point.
- A company is not called a failure solely because cash fell or losses occurred.
- The current prototype does not claim a statistically validated prediction score. It provides auditable descriptive analysis.
- Live XBRL tag coverage is intentionally limited to common US-GAAP tags; unusual filings can complete with limits.

## Concrete tests

- `api/tests/test_analysis.py` verifies derived burn and quarter-change labels, conservative outcome selection, robust inflection detection, and number/citation claim guards.
- `api/tests/test_graph.py` verifies a live-style metric using `evidence_key` produces an inflection linked to that same `E-...` receipt.
- The same graph tests verify a `distress_without_failure` result keeps the financial receipts behind its label.
- `api/tests/test_api_replay.py` verifies WeWork's replay outcome is `bankruptcy`.
- The Carvana fixture is the survivor-control regression case: it must remain `distress_without_failure`.
