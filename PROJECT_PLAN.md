# Reverse Engineer a Business Failure: Project Plan

> Hackathon prototype · Python + LangGraph backend · Next.js frontend · demo-first, not production
> Companion file: `architecture.md` (implementation reference). This file covers scope, features, delivery and demo.

---

## 1. Summary

**One line:** An AI investigator that rebuilds how a company declined, shows the evidence behind every claim, and says clearly what it cannot prove.

**Problem:** Failure post-mortems are written from memory, after the fact, and mix facts with opinion. Investors and lenders want the warning signs and the likely causes, with sources.

**Solution:** The user picks a company. In minutes they get:

- a dated, evidence-backed timeline
- the financial decline (revenue, cash, net loss, burn)
- the turning points
- several competing explanations, with evidence for and against
- a match to known failure patterns
- a printable report where every claim links to a source

**What we promise:** We identify *likely contributing causes*. We never claim one decision definitively killed a company, because public data cannot prove that.

**Users:** VCs, PE firms, lenders, due-diligence analysts.

---

## 2. Goals and non-goals

### Demo goals

1. A 3-minute demo that works every time, offline if needed (replay mode).
2. Real public data (SEC EDGAR filings, XBRL numbers, public news).
3. Visible trust features: evidence receipts, a verification score, competing hypotheses, a survivor control.
4. One command to run: `docker compose up`.

### Non-goals

- Login, billing, multi-tenant security, Kubernetes, microservices
- Private-company financials (stretch only, via uploaded documents)
- LinkedIn or Glassdoor scraping, employee-review data
- A bankruptcy-probability score
- Long-term agent memory, multi-agent chat, human-review workflow

---

## 3. Scope and demo cases

| Role | Candidate companies | Notes |
|---|---|---|
| Failures (3) | WeWork, Bed Bath & Beyond, Bird Global | Confirm filings, 8-Ks and XBRL data exist before committing |
| Survivor control (1) | Carvana or Peloton | Severe stress, no failure. The system must not call it a failure |

All four are pre-run, saved to the database, and cached in `fixtures/`.

**Also verify:** SEC's company search may not list bankrupt or delisted companies. Hard-code the CIKs of the 4 demo companies.

---

## 4. Features

### Must have (P0)

| # | Feature | What the user sees |
|---|---|---|
| 1 | Company search + confirm | Type a name, pick the right legal entity |
| 2 | Live agent progress | Real node status (Running, Done, Skipped, Failed) over WebSocket, no fake percentages |
| 3 | Evidence-backed timeline | Dated events with source link and quote |
| 4 | Financial charts | Revenue, cash, net loss, burn. Disclosed vs derived values styled differently |
| 5 | Inflection points | Turning points on the chart, with a note that timing is not proof of cause |
| 6 | Outcome assessment | What happened (bankruptcy, delisting, going-concern warning, or none) |
| 7 | Competing hypotheses | 3 cards: mechanism, evidence for, evidence against, missing evidence, confidence |
| 8 | Verification score | 'Claims checked: 41, supported: 38, removed: 3' |
| 9 | Pattern match | Closest archetype plus 2 similar cases, similarities and differences listed |
| 10 | Report | Printable page, every claim clickable to its source |

### Nice to have (P1)

- Side-by-side: failed company vs survivor
- 'What would change this conclusion?' on each hypothesis
- Run cost and token counter in the UI
- Name-masked mode (shows the model reasons from evidence, not memory)

### Cut order if behind

1. Compare view
2. Name-masked mode
3. Pattern-match depth
4. PDF polish

**Never cut:** evidence-linked timeline, verification, competing hypotheses.

---

## 5. How it works

One LangGraph graph. Each agent is a node; data moves through a typed shared state. Full detail is in `architecture.md`.

```text
Company confirmed in UI (before the graph starts)
START
  → resolve_company
  → collect                 SEC filings + Exa search
  → extract_events          Cerebras + rules          ┐ parallel
  → compute_financials      XBRL + pandas             ┘ (join before next node)
  → assess_outcome          what actually happened?   [added after review]
  → detect_inflections      statistics + short explanation
  → propose_hypotheses ─┐   also outputs atomic claims
  → critic              │   max 2 rounds
  → verify_claims ──────┘   back only if blockers remain
  → match_patterns
  → write_report
END
```

### Key design ideas

1. **Evidence IDs.** Every stored chunk gets an ID (`E-001`...). Every claim cites IDs. No valid ID, claim dropped.
2. **Rules before AI.** SEC XBRL numbers, 8-K item types (1.03, 2.05, 3.01, 4.02, 5.02) and 'substantial doubt about going concern' language come first. The LLM interprets.
3. **Statistics find turning points, AI explains them.** Timing is never proof of cause.
4. **Hypothesis loop.** Propose 3, critic tries to refute, final confidence label. 'Insufficient evidence' is a valid answer.
5. **Three-layer verification.** Quote exists in source; dates and numbers match filing data; a reasoning check confirms the source supports the claim.
6. **Pattern matching with differences.** About 8 archetypes and 12 hand-written cases, embedded. May answer 'no good match'.
7. **Fixed budgets.** Caps on calls, tokens, retries and loop rounds.

---

## 6. Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind, shadcn/ui, Recharts |
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| Orchestration | LangGraph (pin one version) |
| Async work | asyncio + httpx |
| Progress | Redis pub/sub |
| Database | PostgreSQL + pgvector |
| Discovery | Exa API |
| Fast extraction | Cerebras API |
| Reasoning + embeddings | OpenAI API |
| Financial data | SEC EDGAR (submissions, Company Facts / XBRL) |
| Calculations | pandas, numpy |
| Tracing (stretch) | LangSmith or Langfuse |
| Packaging | Docker Compose |
| PDF | Browser print stylesheet |

**Verify before building:** Cerebras endpoint, model names and structured-output support; SEC User-Agent and current rate limits; Exa endpoints and credits; LangGraph stream mode names; tracing-tool free-tier limits and data settings. Keep model names, prices and limits in config, not code.

---

## 7. Decisions to lock before coding

These came out of the architecture review. Starting defaults are suggestions; tune them with real data.

| Decision | Starting default |
|---|---|
| **Outcome rule** | Failure = 8-K 1.03 bankruptcy, delisting notice, or going-concern warning followed by wind-down. Otherwise 'distress without failure' and no cause is invented |
| **Who creates claims** | `propose_hypotheses` outputs atomic claims with evidence IDs; `verify_claims` checks them; `write_report` uses only supported ones |
| **Early checks** | `extract_events` runs quote-match and date-parse checks, so later nodes only receive checked facts |
| **Evidence IDs** | UUID primary key plus a per-run `E-001` key |
| **Confidence: High** | At least 2 independent sources including a primary filing, mechanism stated, contrary evidence addressed |
| **Confidence: Moderate** | One primary source or several secondary, some alternatives still open |
| **Confidence: Low** | Indirect or single secondary source |
| **Confidence: Insufficient** | Cannot be supported; reported as such |
| **Inflection method** | Rolling MAD on quarter-over-quarter change; about 8-quarter window; flag about 3 robust z-scores; need at least 6 quarters, else qualitative only |
| **Collection** | Forms 10-K, 10-Q, 8-K, S-1; analysis window set per run; chunks about 800 tokens with 100 overlap |
| **Budgets per run** | About 25 Exa searches, about 60 documents, 2 critic rounds, 2 retries per call |
| **Cache roles** | Redis for progress only; `fixtures/` for saved API responses; `record` mode writes them, `replay` reads them |
| **WebSocket** | On connect, send current node status from the database, then stream new events |
| **Parallel nodes** | Separate state keys or reducers so parallel nodes do not overwrite each other |
| **Types** | Generate TypeScript types from FastAPI's OpenAPI schema |
| **Failure states** | Add `completed_with_limits`; define behavior for no XBRL, Exa down, rate limit, invalid JSON twice, too few events |

---

## 8. Build plan

Written for about 36 hours. Stretch or squeeze to your hackathon length.

| Block | Hours | Goal | Done when |
|---|---|---|---|
| 1. Setup + spike | 0-3 | Repo, compose, keys; call SEC, Exa, Cerebras, OpenAI once; stub graph with 3 nodes streaming to the browser | One script prints data from all four; stub progress shows in UI |
| 2. Collect + store | 3-9 | SEC filings, 8-Ks, XBRL; Exa search; chunk, hash, store with evidence IDs | First company's sources in Postgres |
| 3. Extract | 9-15 | Cerebras event extraction with Pydantic schemas; early quote and date checks; dedupe | Timeline matches hand-checked events |
| 4. Analyze | 15-20 | Metrics, outcome assessment, inflections | Chart data, outcome label, 2-3 sensible turning points |
| 5. Explain + verify | 20-27 | Propose (with claims), critic, verify, bounded loop | Verification score computed |
| 6. Frontend | 14-32 (parallel) | Six screens | Click-through demo on a cached run |
| 7. Patterns | 27-30 | 8 archetypes, 12 cases, matcher | Match shown with differences |
| 8. Polish + rehearse | 32-36 | Record fixtures, replay mode, backup video, 3 rehearsals | Demo runs fully offline |

**Team of 3:** one on graph and agent nodes, one on SEC data, analysis and verification, one on frontend and demo.
**Solo:** backend first on one company; freeze the UI design early.
**Scope freeze:** around hour 20.

---

## 9. Demo script (3 minutes)

| Time | Show | Message |
|---|---|---|
| 0:00-0:25 | The problem | Post-mortems are stories; investors need evidence |
| 0:25-1:15 | Pre-run case: timeline, cash chart, turning points | Dates, numbers, sources |
| 1:15-2:00 | Open a hypothesis, click a claim, see the highlighted source | Every claim has a receipt |
| 2:00-2:30 | Live run on a second company (fallback: replay) | Multi-agent and fast |
| 2:30-2:50 | Survivor control: similar warning signs, no failure declared | Not a doom machine |
| 2:50-3:00 | Limits stated honestly, next steps | Trustworthy |

Backup: recorded video plus replay mode.

---

## 10. Risks and fixes

| Risk | Fix |
|---|---|
| API failure or rate limit during demo | Replay mode, backup video |
| LangGraph version changes or confusing errors | Pin version, keep nodes as plain functions, build the stub graph in hour 1 |
| Messy PDFs and tables | Use XBRL numbers and 8-K items; avoid free-form table parsing |
| AI invents facts | Evidence IDs, quote matching, removal of unsupported claims |
| Overclaiming a cause | Competing hypotheses, critic, 'Insufficient' as valid |
| Model already knows famous failures | Include a lesser-known case, masked mode, require citations |
| Async rate-limit errors | Per-provider semaphores, backoff, caching |
| Missed events on WebSocket | Send stored status on connect |
| Time overrun | Cut list; freeze scope at hour 20 |
| API cost | Run caps, caching, small case set |
| Terms of service | No LinkedIn or Glassdoor scraping; official and API sources only |
| Fixtures hold third-party news text | Keep quotes short or keep fixtures private |

---

## 11. Quick evaluation

- Hand-check 10 events per case (date and source)
- Spot-check 5 financial values per case against the filing
- Verification rate: supported vs removed claims
- Survivor test: does the system avoid declaring failure?
- Time and cost per run
- One smoke test running the full graph in replay mode

Report results honestly. The sample is small: call it a prototype test, not proof of accuracy.

---

## 12. Before the hackathon

- [ ] Read the rules (some require all code written during the event; research and design prep are usually fine)
- [ ] Create API keys; check credits and limits for OpenAI, Cerebras, Exa
- [ ] Read the current LangGraph quickstart; pin a version
- [ ] Confirm filings, 8-Ks and XBRL data for all 4 demo companies; note their CIKs
- [ ] Write notes for 8 archetypes and 12 cases from reliable sources
- [ ] Prepare the SEC User-Agent string
- [ ] Sketch the 6 screens on paper
- [ ] Decide roles and the cut list
- [ ] Prepare `.env.example` and the compose file layout

## 13. Demo-day checklist

- [ ] Fixtures recorded for all 4 cases; replay mode tested with Wi-Fi off
- [ ] Backup video recorded
- [ ] Survivor case behaves correctly
- [ ] Click path rehearsed: claim, quote, source
- [ ] API keys not in git; source text rendered as plain text
- [ ] Limits slide ready

---

## 14. Pitch lines and honest limits

- **Evidence, not storytelling:** every claim is a receipt
- **Honest about uncertainty:** competing hypotheses and 'insufficient evidence'
- **Survivor control:** warning signs do not automatically mean failure
- **Built for due diligence:** VCs, lenders and PE

**Say out loud:** public data only; private startups need uploaded documents; findings are likely contributing causes, not proven causes; not financial advice.
