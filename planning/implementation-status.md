# Implementation status — 2026-11-01

This record explains what is currently built, in plain language, and what still needs a real-environment check.

## What works now

- The FastAPI service stores research runs, sources, evidence, events, financial metrics, outcomes, claims, conversations, and text-only assistant transcripts.
- Replay mode loads four synthetic, evidence-shaped cases: WeWork, Bed Bath & Beyond, Bird Global, and the Carvana survivor control.
- Deterministic code calculates derived financial values, finds unusually large quarter-to-quarter changes, and makes conservative outcome assessments.
- A pinned LangGraph workflow runs the research stages, has a maximum of two revision rounds, and keeps rejected claims out of downstream state and reports.
- The Next.js app shows search, graph progress, charts, timeline, outcomes, hypotheses, evidence drawer, printable report, grounded chat, and push-to-talk controls.
- Sarvam requests remain server-side. Chat only receives approved evidence context; microphone bytes and synthesized audio are not stored.

## Code map

| Area | Main implementation | Plain-language responsibility |
| --- | --- | --- |
| API and persistence | `api/app/main.py`, `models.py`, `routes/`, `services/` | Starts the service, exposes endpoints, and stores run data. |
| Evidence and providers | `api/app/providers/`, `services/replay.py` | Fetches or replays public-source material and gives it an evidence receipt. |
| Analysis | `api/app/analysis/` | Calculates numbers and conservative outcomes before AI reasoning. |
| Research graph | `api/app/graph/` | Orders stages, limits revisions, and prevents unsupported claims from reaching reports. |
| Sarvam assistant | `api/app/services/conversation.py`, `providers/sarvam.py` | Answers only from approved run evidence and handles transient voice input/output. |
| Web application | `web/app/`, `web/components/`, `web/lib/` | Displays research results and converts API records into accessible dashboard views. |
| Demo data | `fixtures/`, `knowledge/` | Supplies four offline cases, eight archetypes, and twelve comparison notes. |

## Deliberate prototype limits

- The API uses SQLAlchemy `create_all` for a fresh demo database; formal Alembic migrations are a follow-up before shared deployment.
- Redis and PostgreSQL are included in Compose. The current WebSocket transport uses safe database polling as a fallback, so the demo can run even if Redis pub/sub is not configured.
- Embeddings are stored as JSON-ready fields and pattern matching uses the local knowledge base. A pgvector index is the next scale-up step.
- Replay fixtures are synthetic summaries with public-style source links. They demonstrate traceability and must not be treated as financial research.
- Replay mode is the default. SEC, Exa, Cerebras, OpenAI, Sarvam chat, and Sarvam TTS passed minimal credential checks on 2026-11-01; browser microphone checks still need English, Hindi, and code-mixed recordings.
- Cerebras model availability is account-specific. `CEREBRAS_MODEL` defaults to `gpt-oss-120b` and must be set to a model exposed by the selected account.

## Current gate state

Phases 0-10 are implemented and tested. They remain `tested`, not `accepted`, until the project owner reviews their recorded gate evidence. The remaining Phase 10 work is browser voice coverage, manual source/event checks, a backup demo video, and owner approval. See individual phase records and `test-results/` for exact evidence.
