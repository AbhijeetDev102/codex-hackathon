"""Run lifecycle helpers. Graph execution is intentionally plugged in by app.graph."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.orm import Session

from ..models import Company, ResearchRun

GRAPH_STAGES = (
    "resolve_company",
    "collect",
    "extract_events",
    "compute_financials",
    "assess_outcome",
    "detect_inflections",
    "propose_hypotheses",
    "critic",
    "verify_claims",
    "match_patterns",
    "write_report",
)

RunExecutor = Callable[[str], Awaitable[None]]
_run_executor: RunExecutor | None = None


def initial_node_status() -> dict[str, str]:
    return {stage: "pending" for stage in GRAPH_STAGES}


def start_run(db: Session, company: Company) -> ResearchRun:
    run = ResearchRun(company_id=company.id, state="queued", node_status=initial_node_status())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def update_node_status(db: Session, run: ResearchRun, node: str, status: str) -> ResearchRun:
    statuses = dict(run.node_status or {})
    statuses[node] = status
    run.node_status = statuses
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def register_run_executor(executor: RunExecutor) -> None:
    """Register the compiled LangGraph runner without coupling routes to graph code."""
    global _run_executor
    _run_executor = executor


async def execute_run(run_id: str) -> bool:
    """Run the registered graph; returns False during foundation-only startup."""
    if _run_executor is None:
        return False
    await _run_executor(run_id)
    return True
