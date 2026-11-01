# Reverse Engineer a Business Failure — Architecture

> Hackathon prototype: Python + LangGraph backend, Next.js frontend, evidence-first analysis. This document is the implementation reference for the project plan.

## Current prototype status

This document describes the intended architecture as well as the shipped demo. The
working implementation is replay-first: it runs four synthetic, evidence-shaped
cases offline and has opt-in live provider adapters. The implementation deliberately
uses SQLAlchemy `create_all` for a fresh demo database, database-polling WebSocket
progress, and deterministic local knowledge matching. PostgreSQL/pgvector, Redis
pub/sub, Alembic migrations, generated OpenAPI TypeScript types, and semantic vector
retrieval remain scale-up work rather than completed claims. See
[`planning/implementation-status.md`](planning/implementation-status.md) for the
plain-language code map and exact phase/test status.

## 1. Purpose and product boundary

The product investigates how a public company declined using public records. A user selects a company and receives a dated evidence-backed timeline, financial trend analysis, inflection points, competing explanations, an archetype match, and a printable report.

The product identifies *likely contributing causes*. It must never state that one action definitively caused a company's failure. Every user-visible claim needs supporting evidence; otherwise it is removed. “Insufficient evidence” is a valid outcome.

Primary users are VCs, PE firms, lenders, and due-diligence analysts.

### In scope for the demo

- Public-company analysis using SEC EDGAR filings, structured XBRL data, and public news.
- Three pre-run failure cases and one survivor/control case, cached for reliable demos.
- A single FastAPI backend, a single Next.js frontend, and `docker compose up` startup.
- One live run when connectivity allows, plus fully offline replay mode.

### Explicitly out of scope

- Authentication, billing, multi-tenant security, payments, Kubernetes, or microservices.
- Private-company financial analysis unless documents are supplied later.
- LinkedIn/Glassdoor scraping, employee-review data, and a bankruptcy-probability score.
- Long-term agent memory, multi-agent chat, or human-review workflows.

## 2. Design principles

1. **Evidence is the source of truth.** Every stored text chunk receives an evidence ID (`E-001`, `E-002`, …). Every claim cites valid evidence IDs.
2. **Rules and numbers precede LLM reasoning.** Use SEC XBRL, filing metadata, 8-K item types, and deterministic calculations before asking an LLM to interpret the data.
3. **Separate correlation from causation.** Inflection-point timing is informative, never proof of cause.
4. **Competing hypotheses over a single narrative.** Generate, critique, and verify several explanations. Include contrary and missing evidence.
5. **Verification is a gate, not decoration.** Unsupported claims never reach the final report.
6. **Bounded cost and execution.** Cap provider calls, tokens, retries, and critic-loop rounds.
7. **External documents are data, never instructions.** Treat fetched text as untrusted content.

## 3. High-level architecture

```text
Browser (Next.js)
  ├─ REST: company search, run data, evidence, report
  └─ WebSocket: live node status
             │
             ▼
FastAPI service
  ├─ REST API + WebSocket handler
  ├─ background run manager
  ├─ LangGraph orchestration
  ├─ provider adapters + cached request wrapper
  └─ analysis and verification modules
       │                 │
       ▼                 ▼
PostgreSQL + pgvector   Redis
companies, evidence,    progress pub/sub,
runs, results, vectors  cache/status fan-out
       │
       ▼
SEC EDGAR / Exa / Cerebras / OpenAI
```

The application is one deployable backend service. A run is launched as a background task and each node persists its result. Redis is included in Compose for the planned pub/sub transport; the current WebSocket handler safely polls persisted run status, so replay works without Redis fan-out.

## 4. Research graph

Entity confirmation happens before the graph: search SEC entities, let the user select the correct legal company, then start a run with its CIK and ticker.

```text
START
  → resolve_company
  → collect ──────────────────────────┐
  → extract_events (Cerebras + rules) │ parallel where inputs allow
  → compute_financials (XBRL + pandas)┘
  → assess_outcome
  → detect_inflections
  → propose_hypotheses → critic → verify_claims
                              ▲        │
                              └────────┘ only if blockers remain and round < 2
  → match_patterns
  → write_report
END
```

### Node responsibilities

| Stage | Node | Input → output | Primary implementation |
| --- | --- | --- | --- |
| 1 | `resolve_company` | name → confirmed entity | SEC lookup; OpenAI only for ambiguity |
| 2 | `collect` | entity → source registry/chunks | SEC EDGAR + Exa using `httpx`/`asyncio` |
| 3 | `extract_events` | chunks → dated, quoted events | Cerebras + rules, Pydantic schema |
| 4 | `compute_financials` | filings → disclosed/derived metrics | SEC Company Facts + pandas |
| 5 | `assess_outcome` | filings/events → bounded outcome assessment | deterministic filing rules |
| 6 | `detect_inflections` | metrics/events → ranked turning points | numpy statistics + short explanation |
| 7 | `propose_hypotheses` / `critic` | verified facts → competing explanations | OpenAI |
| 8 | `verify_claims` | claims → supported or removed | quote/date/math checks + OpenAI entailment check |
| 9 | `match_patterns` | hypotheses → archetype and analogous cases | embeddings, pgvector, OpenAI |
| 10 | `write_report` | approved claims → report JSON | OpenAI |

Use a typed shared graph state. Nodes are plain async functions that return only fields they changed; business logic remains in ordinary, independently testable Python modules.

```python
class RunState(TypedDict):
    run_id: str
    company: Company
    sources: list[Source]
    events: list[Event]
    metrics: list[Metric]
    outcome: OutcomeAssessment
    inflections: list[Inflection]
    hypotheses: list[Hypothesis]
    verification: VerificationReport
    revise_round: int
    report: Report | None
```

The conditional edge after verification is the only feedback loop. It may return to hypothesis generation only when unresolved blockers remain and `revise_round < 2`; otherwise the graph continues. All LLM node outputs must validate as Pydantic models. Allow one repair attempt, then mark the node failed cleanly.

## 5. Analysis and trust model

### Evidence and verification

- Store chunks with source URL, publication date, quote span, content hash, and evidence ID.
- A claim is admissible only when it cites evidence and passes all three checks:
  1. the quoted text occurs in the recorded source;
  2. cited dates and numbers agree with filing/metric data;
  3. a reasoning check confirms the source actually supports the claim.
- Record supported and removed claims to calculate the verification score.

### Financial and event signals

- Prefer structured SEC XBRL figures for revenue, cash, net loss, and burn/operating cash flow.
- Label values as `disclosed` or `derived`; do not visually present calculated values as filing disclosures.
- Give special treatment to 8-K items 1.03, 2.05, 3.01, 4.02, and 5.02, plus “substantial doubt about going concern” language.
- Calculate quarter-over-quarter changes and detect unusual movement using robust measures such as median absolute deviation or CUSUM.
- Align candidate turning points with dated events in an approximately one-quarter window, clearly noting this is not causal proof.

### Outcome assessment

`assess_outcome` is deterministic and evidence-linked. It may return `bankruptcy`, `delisted`, `wound_down`, `going_concern`, `distress_without_failure`, or `unknown`, along with the evidence IDs and a short explanation. A distressed company must not be called a failure unless its filings support the outcome rule.

### Pattern matching

Maintain roughly eight failure archetypes and twelve hand-written historical cases in the knowledge base. The current prototype makes an explicit local-signal comparison and returns similarities/differences; a future scale-up can add embeddings and pgvector retrieval. Results may return “no good match.” Pattern matching must not be presented as proof of causation.

## 6. Data model

| Table | Core fields |
| --- | --- |
| `companies` | id, legal_name, cik, ticker, website, status |
| `runs` | id, company_id, state, node_status (JSON), cost, started_at |
| `sources` | id, run_id, url, publisher, published_at, type |
| `evidence` | id (`E-001`), source_id, text, quote_span, content_hash, embedding |
| `events` | id, run_id, date, date_precision, category, description, evidence_ids, confidence |
| `metrics` | id, run_id, metric, period, value, unit, kind, evidence_id |
| `inflections` | id, run_id, period, metric, size, explanation, evidence_ids |
| `outcomes` | id, run_id, status, explanation, evidence_ids |
| `hypotheses` | id, run_id, mechanism, supports, contradicts, missing, confidence, critic_notes |
| `archetypes`, `cases` | definition/signals and embedded case summaries |
| `claims`, `verifications` | claim text, cited evidence, result, reason |

Store final report JSON on the associated `runs` record. PostgreSQL with pgvector provides both transactional evidence storage and semantic pattern retrieval.

## 7. APIs and real-time progress

| Endpoint | Purpose |
| --- | --- |
| `GET /api/companies/search?q=` | Return legal entities for user confirmation. |
| `POST /api/research` | Start a run for a confirmed company; return run ID. |
| `GET /api/research/{id}` | Return run status and per-node state. |
| `GET /api/research/{id}/outcome` | Return the evidence-linked outcome assessment. |
| `WS /ws/research/{id}` | Stream real node updates (`Running`, `Done`, `Skipped`, `Failed`). |
| `GET /api/research/{id}/{timeline,financials,inflections,hypotheses,patterns,claims}` | Return dashboard sections. |
| `GET /api/research/evidence/{id}` | Return source text, quote location, and original link. |
| `GET /api/research/{id}/report` | Return final report JSON. |
| `POST /api/research/{id}/assistant/messages` | Stream an evidence-grounded Sarvam chat response. |
| `POST /api/research/{id}/assistant/transcriptions` | Transcribe a short voice question without retaining audio. |
| `POST /api/research/{id}/assistant/speech` | Stream speech for an approved assistant response. |

The current WebSocket emits persisted node status by database polling. A Redis-backed LangGraph event channel is the planned scale-up path. Show actual stages and result counts in the UI—never invented progress percentages.

## 8. Frontend experience

1. **Home:** company search plus four saved-case cards (three failures, one survivor).
2. **Progress:** vertically ordered graph nodes, real-time status, source counts.
3. **Dashboard:** company identity, financial chart with inflection markers, and evidence-backed timeline.
4. **Failure analysis:** three hypothesis cards, archetype result, and verification score.
5. **Evidence drawer:** clicking a claim opens the source with its supporting quote highlighted.
6. **Report:** clean printable output using a browser print stylesheet.
7. **Research assistant:** optional run-scoped English/Hindi chat and push-to-talk voice interface. Every factual answer visibly cites evidence; it cannot edit the report or start a run.

The current UI uses Next.js, TypeScript, custom CSS, and accessible SVG charts; it does not claim Tailwind, shadcn/ui, or Recharts. Core demo content is the evidence-linked timeline, verification, and competing hypotheses; cut comparison view, masked mode, deeper pattern matching, then PDF export if time is constrained.

## 9. Providers, caching, and configuration

- **SEC EDGAR:** filings, submissions, and Company Facts/XBRL. Send a descriptive User-Agent and respect current documented rate limits.
- **Exa:** discovery of relevant reporting, announcements, and company pages.
- **Cerebras:** fast parallel chunk classification and event extraction.
- **OpenAI:** hypothesis generation, criticism, verification, reporting, and embeddings.
- **Sarvam:** read-only, evidence-grounded run conversation; Saaras speech-to-text and Bulbul text-to-speech for optional voice interaction.

Provider access goes through narrow interfaces such as `Discovery`, `Extractor`, and `Reasoner`. Keep endpoints, model names, prices, limits, and feature flags in configuration rather than application code. Apply per-provider semaphores, backoff/retries, request caps, token caps, and a two-round revision limit.

Sarvam is kept outside the research graph behind `ConversationProvider`, `SpeechToTextProvider`, and `TextToSpeechProvider`. It receives only verified run data, persists text transcripts and citations, and processes microphone audio transiently. If a citation cannot be validated against approved evidence, the response is rejected and replaced with an uncertainty message.

Every external call is routed through one cached wrapper keyed by a request hash. With `DEMO_MODE=replay`, serve captured responses from `fixtures/` instead of reaching the network. Replay mode must power the full demo offline, quickly, and without additional cost.

## 10. Repository layout

```text
/web                 Next.js application
/api
  /app/main.py       FastAPI REST and WebSocket entry point
  /app/graph/        LangGraph state, nodes, and edges
  /app/services/     replay loading, run lifecycle, and conversations
  /app/providers/    SEC, Exa, Cerebras, OpenAI clients and cache wrapper
  /app/providers/    Sarvam conversation, transcription, and speech adapters
  /app/analysis/     metrics, change points, verification checks
  /app/db.py         SQLAlchemy engine and sessions
/prompts             versioned agent prompts
/knowledge           archetypes and case notes
/fixtures            saved provider responses for replay mode
/planning            phase records, plain-language component docs and test evidence
/docker-compose.yml  one-command startup
```

## 11. Delivery and quality bar

The target is a reliable three-minute demo. Demonstrate a pre-run case, click from a claim to an evidence quote, show a live/replay graph run, and contrast it with a survivor control. Keep a recorded fallback video.

Before demo day, hand-check ten events per case, five financial values per case, the supported/removed claim rate, survivor behavior, and time/cost per run. Report the small sample honestly as prototype evaluation—not proof of model accuracy.

The final product statement is: **evidence, not storytelling; likely contributors, not proven causes; public data only; not financial advice.**
