# Phase 1 — Foundation

**Status:** tested

## Goal

Create a small, repeatable application shell that starts locally with one command.

## Scope

- Create `/api` (FastAPI) and `/web` (Next.js) applications.
- Add Docker Compose with PostgreSQL and Redis.
- Add settings validation, `.env.example`, migrations, health endpoints, API schemas, provider interfaces, and test setup.
- Generate frontend API types from FastAPI OpenAPI during development or CI.

## Gate

`docker compose up` starts all services on a clean setup. Health, migration, mocked-provider, and frontend smoke tests pass. Record output in `test-results/phase-01.md`.

## Implementation record

- Code: `/api/app/main.py`, `/api/app/config.py`, `/api/app/db.py`, `/web/`, and `/docker-compose.yml`.
- Inputs: environment variables and Compose service URLs. Outputs: health endpoints, API schema, web app, and local database tables.
- Tests: backend API replay test; frontend typecheck, Vitest, and production build passed.
- Known limit: `create_all` is used for the demo database instead of versioned migrations. The full Compose check passed on 2026-11-01.
