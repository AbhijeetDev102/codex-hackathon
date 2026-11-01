# Platform foundation

## In simple language

The platform foundation starts the API, web app, database, and Redis together. It also makes the app usable without paid API keys by starting in replay mode with saved demo data.

## Implemented code map

- `/docker-compose.yml` starts PostgreSQL with pgvector, Redis, the FastAPI API, and the Next.js web app.
- `/api/Dockerfile` and `/web/Dockerfile` build the two application containers.
- `/api/app/main.py` creates FastAPI, initialises the database, seeds demo companies, registers the graph runner, enables CORS, and exposes `/api/health` plus Docker's `/healthz` check.
- `/api/app/config.py` reads configuration such as `DATABASE_URL`, `DEMO_MODE`, `FIXTURES_DIR`, CORS origins, provider keys, the account-selectable `CEREBRAS_MODEL`, and voice limits. `APP_ENV` and `ENVIRONMENT` are both accepted.
- `/api/app/db.py`, `/api/app/models.py`, and `/api/app/schemas.py` define database setup, persistent records, and typed API contracts.
- `/api/pyproject.toml` restricts package discovery to `app*`, so an editable install remains clean even after local SQLite data has been created.
- `/api/app/dependencies.py` builds per-request cache and Sarvam-provider dependencies.

## Data flow and dependencies

1. Docker starts PostgreSQL and Redis before the API.
2. FastAPI creates tables with SQLAlchemy on startup and adds the four saved demo companies when missing.
3. The web app calls the API on port 8000; the API owns all secret provider keys.
4. In `DEMO_MODE=replay`, the API reads `/fixtures/demo_cases.json` mounted read-only at `/fixtures` instead of making live provider calls.

PostgreSQL is the source of truth for runs and evidence. Redis is provisioned for future pub/sub progress delivery; the current WebSocket safely polls persisted run status as a fallback, so live progress does not depend on Redis being available.

## Safe failures and limits

- Optional provider keys are not required for startup. Missing keys disable only the affected live feature and leave replay mode usable.
- Database startup failures stop the API rather than serving incomplete data.
- CORS allows only configured origins, and neither `.env` nor API keys are returned by routes.
- The prototype currently uses SQLAlchemy `create_all`, not versioned Alembic migrations. Add migrations before shared or long-lived deployment.

## Concrete tests

- `docker compose config` validates service, fixture-volume, environment, and healthcheck wiring.
- `docker compose up --build -d` was run successfully on 2026-11-01: PostgreSQL, Redis, API, and web all reached their healthy/running states.
- `GET /api/health` verifies application configuration; `GET /healthz` is used by the Compose healthcheck.
- `api/tests/test_api_replay.py` starts the FastAPI app, finds a demo company, creates a replay run, and reads its outcome and evidence.
- The backend test suite uses SQLite in memory for fast unit/integration coverage; Compose is the PostgreSQL smoke-test path.
