"""Research-run endpoints and a database-polling WebSocket fallback for progress."""

from __future__ import annotations

import asyncio
import json

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import SessionLocal, get_db
from ..models import (
    Claim,
    Company,
    Event,
    Evidence,
    Hypothesis,
    Inflection,
    Metric,
    OutcomeAssessment,
    ResearchRun,
    Source,
)
from ..schemas import (
    ClaimRead,
    ClaimsResponse,
    EventRead,
    EvidenceRead,
    FinancialsResponse,
    HypothesesResponse,
    HypothesisRead,
    InflectionRead,
    InflectionsResponse,
    MetricRead,
    OutcomeRead,
    OutcomeResponse,
    ReportResponse,
    ResearchStartRequest,
    ResearchStartResponse,
    ResearchStatusResponse,
    SourceRead,
    TimelineResponse,
)
from ..services.replay import load_replay_case
from ..services.repository import get_run_or_none
from ..services.research import execute_run, start_run

router = APIRouter(prefix="/research", tags=["research"])
ws_router = APIRouter(tags=["research"])


def _not_found(kind: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "not_found", "message": f"{kind} was not found."})


def _status(run: ResearchRun) -> ResearchStatusResponse:
    return ResearchStatusResponse(
        id=run.id,
        company_id=run.company_id,
        state=run.state,
        node_status=run.node_status or {},
        cost=run.cost,
        error_code=run.error_code,
        error_message=run.error_message,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _load_replay_task(run_id: str, fixtures_dir) -> None:
    db = SessionLocal()
    try:
        run = db.get(ResearchRun, run_id)
        if not run:
            return
        company = db.get(Company, run.company_id)
        if not company or not load_replay_case(db, run, company, fixtures_dir):
            run.state = "completed_with_limits"
            run.error_code = "replay_fixture_missing"
            run.error_message = "No replay fixture is available for this company."
            db.add(run)
            db.commit()
    finally:
        db.close()


@router.post("", response_model=ResearchStartResponse, status_code=202)
def create_research_run(
    request: ResearchStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ResearchStartResponse:
    company = db.get(Company, request.company_id)
    # Accept a stable public CIK as a fallback for bundled replay-company cards.
    # Search results still send the database ID, so this only widens compatibility
    # without changing the normal live-search path.
    if not company and request.cik:
        company = db.scalar(select(Company).where(Company.cik == request.cik))
    if not company:
        raise _not_found("Company")
    run = start_run(db, company)
    if settings.is_replay or request.use_replay:
        background_tasks.add_task(_load_replay_task, run.id, settings.fixture_path)
    else:
        background_tasks.add_task(execute_run, run.id)
    return ResearchStartResponse(id=run.id, state=run.state, company=company)


@router.get("/{run_id}", response_model=ResearchStatusResponse)
def get_research_run(run_id: str, db: Session = Depends(get_db)) -> ResearchStatusResponse:
    run = get_run_or_none(db, run_id)
    if not run:
        raise _not_found("Research run")
    return _status(run)


@router.get("/{run_id}/timeline", response_model=TimelineResponse)
def get_timeline(run_id: str, db: Session = Depends(get_db)) -> TimelineResponse:
    if not get_run_or_none(db, run_id):
        raise _not_found("Research run")
    events = db.scalars(select(Event).where(Event.run_id == run_id).order_by(Event.date)).all()
    return TimelineResponse(events=[EventRead.model_validate(event) for event in events])


@router.get("/{run_id}/financials", response_model=FinancialsResponse)
def get_financials(run_id: str, db: Session = Depends(get_db)) -> FinancialsResponse:
    if not get_run_or_none(db, run_id):
        raise _not_found("Research run")
    metrics = db.scalars(select(Metric).where(Metric.run_id == run_id).order_by(Metric.period)).all()
    return FinancialsResponse(metrics=[MetricRead.model_validate(metric) for metric in metrics])


@router.get("/{run_id}/outcome", response_model=OutcomeResponse)
def get_outcome(run_id: str, db: Session = Depends(get_db)) -> OutcomeResponse:
    if not get_run_or_none(db, run_id):
        raise _not_found("Research run")
    outcome = db.scalar(select(OutcomeAssessment).where(OutcomeAssessment.run_id == run_id))
    return OutcomeResponse(outcome=OutcomeRead.model_validate(outcome) if outcome else None)


@router.get("/{run_id}/inflections", response_model=InflectionsResponse)
def get_inflections(run_id: str, db: Session = Depends(get_db)) -> InflectionsResponse:
    if not get_run_or_none(db, run_id):
        raise _not_found("Research run")
    inflections = db.scalars(select(Inflection).where(Inflection.run_id == run_id)).all()
    return InflectionsResponse(inflections=[InflectionRead.model_validate(item) for item in inflections])


@router.get("/{run_id}/hypotheses", response_model=HypothesesResponse)
def get_hypotheses(run_id: str, db: Session = Depends(get_db)) -> HypothesesResponse:
    if not get_run_or_none(db, run_id):
        raise _not_found("Research run")
    hypotheses = db.scalars(select(Hypothesis).where(Hypothesis.run_id == run_id)).all()
    return HypothesesResponse(hypotheses=[HypothesisRead.model_validate(item) for item in hypotheses])


@router.get("/{run_id}/claims", response_model=ClaimsResponse)
def get_claims(run_id: str, db: Session = Depends(get_db)) -> ClaimsResponse:
    if not get_run_or_none(db, run_id):
        raise _not_found("Research run")
    claims = db.scalars(select(Claim).where(Claim.run_id == run_id)).all()
    return ClaimsResponse(claims=[ClaimRead.model_validate(item) for item in claims])


@router.get("/{run_id}/patterns")
def get_patterns(run_id: str, db: Session = Depends(get_db)) -> dict:
    run = get_run_or_none(db, run_id)
    if not run:
        raise _not_found("Research run")
    match = (run.final_report or {}).get("pattern_match")
    if not match:
        return {"archetype": None, "similar_cases": [], "status": "not_available"}
    return {"status": "available", **match}


@router.get("/{run_id}/report", response_model=ReportResponse)
def get_report(run_id: str, db: Session = Depends(get_db)) -> ReportResponse:
    run = get_run_or_none(db, run_id)
    if not run:
        raise _not_found("Research run")
    return ReportResponse(report=run.final_report)


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence(
    evidence_id: str, run_id: str | None = Query(default=None), db: Session = Depends(get_db)
) -> EvidenceRead:
    statement = select(Evidence).where(or_(Evidence.id == evidence_id, Evidence.evidence_key == evidence_id))
    if run_id:
        statement = statement.where(Evidence.run_id == run_id)
    evidence = db.scalar(statement.order_by(Evidence.created_at.desc()))
    if not evidence:
        raise _not_found("Evidence")
    source = db.get(Source, evidence.source_id)
    return EvidenceRead(
        id=evidence.id,
        evidence_key=evidence.evidence_key,
        source_id=evidence.source_id,
        text=evidence.text,
        quote_start=evidence.quote_start,
        quote_end=evidence.quote_end,
        source=SourceRead.model_validate(source) if source else None,
    )


@ws_router.websocket("/ws/research/{run_id}")
async def research_progress(websocket: WebSocket, run_id: str) -> None:
    """Works without Redis; a future Redis subscriber can replace only this transport layer."""
    await websocket.accept()
    last_payload: str | None = None
    try:
        while True:
            db = SessionLocal()
            try:
                run = db.get(ResearchRun, run_id)
                if not run:
                    await websocket.send_json({"type": "error", "code": "not_found"})
                    return
                payload = _status(run).model_dump(mode="json")
            finally:
                db.close()
            serialized = json.dumps(payload, sort_keys=True)
            if serialized != last_payload:
                await websocket.send_json({"type": "research.status", "data": payload})
                last_payload = serialized
            await asyncio.sleep(0.75)
    except WebSocketDisconnect:
        return
