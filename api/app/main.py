"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import SessionLocal, init_db
from .routes import assistant, companies, health, research
from .services.repository import ensure_demo_companies
from .services.research import register_run_executor


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        ensure_demo_companies(db)
    finally:
        db.close()

    # Graph code is optional during the foundation phase. When present, it owns live runs;
    # replay runs are loaded directly from fixtures by the research route.
    try:
        from .graph.runner import run_research
    except ModuleNotFoundError as error:
        # The module genuinely is optional only while the foundation is being built.
        if error.name not in {"app.graph.runner", ".graph.runner"}:
            raise
    else:
        register_run_executor(run_research)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(companies.router, prefix=settings.api_prefix)
app.include_router(research.router, prefix=settings.api_prefix)
app.include_router(assistant.router, prefix=settings.api_prefix)
app.include_router(research.ws_router)


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs", "health": f"{settings.api_prefix}/health"}


@app.get("/healthz", tags=["health"])
def container_healthcheck() -> dict[str, str]:
    """Small unauthenticated endpoint used solely by Docker's service healthcheck."""
    return {"status": "ok"}
