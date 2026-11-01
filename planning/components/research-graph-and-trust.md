# Research graph and trust controls

## In simple language

This is the ordered checklist the system follows to research a company. It saves its progress, checks claims against receipts, and removes claims that it cannot support.

## Implemented code map

- `/api/app/graph/state.py` defines the shared `RunState` passed between nodes.
- `/api/app/graph/workflow.py` builds the LangGraph flow: resolve company, collect, extract events, compute financials, assess outcome, detect inflections, propose, critic, verify, match patterns, and write report.
- `/api/app/graph/nodes.py` supplies safe deterministic defaults and builds the final report from supported claims only.
- `/api/app/graph/runner.py` supplies live provider handlers, persists results, updates node status, and marks partial runs as `completed_with_limits`.
- `/api/app/analysis/verification.py` is the deterministic citation and numeric guard.
- `/api/app/models.py` stores runs, hypotheses, claims, outcomes, events, metrics, and final report JSON.

## Data flow and storage

1. The research route creates a `runs` record with every node marked `pending`.
2. The graph sets nodes to `running`, `done`, or `failed`; the browser receives persisted status through `/ws/research/{run_id}`.
3. Deterministic collection and analysis run before optional model reasoning.
4. Proposed claims must cite known `E-...` keys. Verification checks the citation exists and that stated numbers occur in the cited text.
5. Unsupported claims are retained as rejected audit records but omitted from the final report.
6. If blockers remain, the graph loops through proposal and verification at most two times before continuing.

Pattern matching currently uses explicit local signals from `/knowledge/archetypes.json` plus the hand-written comparison notes in `/knowledge/cases.json`. A qualifying match is included in the final report and `/patterns` response with up to two comparable cases, their shared signals, and differences to check. It is an honest deterministic prototype replacement for the planned embedding/pgvector matcher.

## Safe failures and limits

- Every node catches errors into visible status and the run can finish with limits instead of silently losing context.
- Missing OpenAI/Cerebras credentials leave the deterministic parts usable; no model-generated hypothesis is required for a valid report.
- The current critic node is a bounded placeholder. The citation verifier is active, but a separate model-driven rebuttal pass remains a future enhancement.
- The final report is deliberately limited to supported claims and includes a public-data/no-causation limitation.

## Concrete tests

- `api/tests/test_graph.py` asserts an unsupported claim is removed from the report, the bounded revision counter stops at two, and the write-report node completes.
- The same graph test module verifies local pattern matching returns two comparable cases and that `pattern_match` reaches the final report.
- `api/tests/test_analysis.py` asserts invalid evidence IDs and unsupported numbers are rejected.
- `api/tests/test_api_replay.py` exercises the stored replay graph result through public routes.
