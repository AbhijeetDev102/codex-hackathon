# Reverse Engineer a Business Failure

An evidence-first hackathon prototype for reconstructing a public company's decline. It shows a source-linked timeline, financial signals, a conservative outcome assessment, competing hypotheses, and a citation-only conversational assistant.

## Run the demo

1. Copy `.env.example` to `.env` if you want to configure live provider keys. The default experience uses safe offline replay data.
2. Start Docker Desktop.
3. Run `docker compose up --build`.
4. Open `http://localhost:3000`.

The application starts in `DEMO_MODE=replay`. It contains synthetic, evidence-shaped demo fixtures for WeWork, Bed Bath & Beyond, Bird Global, and the Carvana survivor control. Fixture content demonstrates product behavior; it is not investment research.

## Live providers

Set `DEMO_MODE=live` and provide the needed keys to enable SEC, Exa, Cerebras, OpenAI, and Sarvam calls. In live mode you can search SEC-reporting U.S. public companies by legal name, ticker, or CIK (for example, `TSLA`). A private company or a company absent from the SEC directory is not currently supported. The app still refuses to put unsupported claims in a report. Sarvam chat is read-only and only sees verified run material; microphone audio is handled transiently and is never stored.

## Project map

- `api/` — FastAPI API, providers, deterministic analysis, LangGraph workflow, and tests.
- `web/` — Next.js dashboard, evidence drawer, and Sarvam chat/voice UI.
- `fixtures/` — offline demo data.
- `knowledge/` — failure archetypes and comparison-case notes.
- `planning/` — phase records, architecture decisions, component explanations, and test evidence in plain language.

Run backend tests with `cd api && python -m pytest -q`; run the frontend checks with `cd web && npm.cmd run typecheck && npm.cmd run test && npm.cmd run build`.
