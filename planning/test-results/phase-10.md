# Phase 10 test result — Final acceptance

**Status:** tested

**Gate:** Awaiting owner approval and the remaining manual acceptance checks.

## Passed locally

- Backend: `ruff check app tests` and `pytest -q` — 16 tests passed.
- Frontend: typecheck, Vitest (5 tests), and production build passed.
- Replay API smoke test passed for health, company lookup, research run, outcome, timeline, evidence retrieval, and grounded chat.
- `docker compose up --build -d` passed: PostgreSQL and Redis became healthy, FastAPI passed `/api/health` and `/healthz`, and the Next.js app served port 3000.
- Live provider probes passed for SEC, Exa, OpenAI, Sarvam chat, Sarvam TTS, and Cerebras structured extraction. Cerebras now uses the account-configurable `CEREBRAS_MODEL` defaulting to `gpt-oss-120b`.
- A live Peloton research run completed every graph stage with no recorded provider error; its assistant endpoint returned a cited server-sent response.

## Remaining acceptance checks

1. Verify the full browser path using offline replay.
2. Complete English, Hindi, and code-mixed microphone tests in a browser.
3. Record a backup demo video and complete the manual source-value/event audit.
4. Approve final acceptance.
