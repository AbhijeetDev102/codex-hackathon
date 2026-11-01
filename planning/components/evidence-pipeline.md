# Evidence pipeline

## In simple language

This code turns source material into small, traceable evidence records. A fact can only be shown when the user can open the source excerpt behind it.

## Implemented code map

- `/api/app/providers/sec.py` searches the official SEC ticker directory in live mode, then fetches SEC submissions and Company Facts with a descriptive User-Agent. The directory result is normalized to legal name, ticker, and CIK before it is saved locally.
- `/api/app/providers/exa.py` performs optional live discovery only when `EXA_API_KEY` is present.
- `/api/app/providers/cache.py` records JSON provider responses or reads matching saved responses in replay mode.
- `/api/app/graph/runner.py` collects XBRL values and 8-K index records, creates `E-...` receipts, and optionally adds Exa excerpts.
- `/api/app/services/repository.py` seeds known companies, stores confirmed public-company lookup results by CIK, and inserts source/evidence records with hashes.
- `/api/app/services/replay.py` loads the four synthetic demo cases from `/fixtures/demo_cases.json`.
- `/api/app/models.py` stores `sources` and `evidence`; `/api/app/routes/research.py` exposes `GET /api/research/evidence/{id}`.

## Data flow and storage

1. A user searches by legal name, ticker, or CIK. In live mode the official SEC directory supplies a matching U.S. SEC-reporting identity; in replay mode only the bounded demo identities are shown.
2. A live run fetches SEC data first and can add Exa results; replay loads a matching case fixture instead.
3. Each source is stored with URL, publisher, type, title, date when available, and a content hash.
4. Each excerpt receives a stable per-run receipt such as `E-001`, text, quote offsets, source link, and hash.
5. Events, metrics, outcomes, claims, and assistant answers refer to the receipt key rather than untraceable prose.

The shipped replay excerpts are intentionally synthetic, short demonstration data. They show the evidence workflow; they are not copies of filings or investment research.

## Safe failures and limits

- Missing SEC/Exa access, absent fixtures, or malformed provider data result in `completed_with_limits` or a clear provider error, never invented evidence.
- A live SEC run currently extracts structured Company Facts and filing-index facts. It does not yet parse full filing bodies or PDF tables.
- Exa is optional: a missing key does not block SEC-backed analysis.
- The SEC submissions index, SEC Company Facts, and supplementary Exa discovery are independent. If one is temporarily unavailable, the run retains the evidence from the others and reports exactly which coverage is limited. It never converts a transport failure into a factual conclusion.
- "Any company" here means a company available in the SEC ticker directory with usable SEC data. Private companies and companies without SEC records are outside the current evidence pipeline.
- The Cerebras extraction model is configurable with `CEREBRAS_MODEL`. Its default is `gpt-oss-120b`; choose a model exposed by the attached Cerebras account rather than hard-coding a retired model ID.
- The cache stores JSON-compatible provider results only. User voice recordings are never cached.

## Concrete tests

- `api/tests/test_api_replay.py` follows a replay event to its evidence endpoint and asserts the receipt key remains intact.
- `api/tests/test_replay_and_conversation.py` loads WeWork fixture data and asserts supported versus unsupported claims retain their evidence receipts.
- `api/tests/test_sec_lookup.py` tests name, ticker, and CIK matching without network access and proves a temporary provider failure preserves the SEC evidence that was retrieved.
- Fixture structure is validated by the data checks documented in `fixtures/README.md`.
