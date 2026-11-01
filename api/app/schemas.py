"""Explicit API contracts shared by routes, services, and generated frontend types."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HealthResponse(APIModel):
    status: Literal["ok"] = "ok"
    service: str
    environment: str
    demo_mode: str


class CompanyRead(APIModel):
    id: str
    legal_name: str
    cik: str | None = None
    ticker: str | None = None
    website: str | None = None
    status: str


class CompanySearchResponse(APIModel):
    results: list[CompanyRead]


class ResearchStartRequest(APIModel):
    company_id: str
    # The dashboard's bundled replay cards use stable short IDs while the database
    # assigns UUIDs. CIK lets the API resolve those cards safely to the seeded row.
    cik: str | None = Field(default=None, min_length=1, max_length=10)
    # Built-in cards are deliberately synthetic, evidence-shaped demo cases.
    # A client must opt in explicitly; arbitrary company searches remain live.
    use_replay: bool = False


class ResearchStartResponse(APIModel):
    id: str
    state: str
    company: CompanyRead


class ResearchStatusResponse(APIModel):
    id: str
    company_id: str
    state: str
    node_status: dict = Field(default_factory=dict)
    cost: float = 0.0
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class SourceRead(APIModel):
    id: str
    url: str
    publisher: str | None = None
    published_at: datetime | None = None
    source_type: str
    title: str | None = None


class EvidenceRead(APIModel):
    id: str
    evidence_key: str
    source_id: str
    text: str
    quote_start: int | None = None
    quote_end: int | None = None
    source: SourceRead | None = None


class EventRead(APIModel):
    id: str
    date: str
    date_precision: str
    category: str
    description: str
    evidence_ids: list[str]
    confidence: str
    verified: bool


class MetricRead(APIModel):
    id: str
    metric: str
    period: str
    value: float
    unit: str
    kind: str
    evidence_id: str | None = None


class OutcomeRead(APIModel):
    status: Literal[
        "bankruptcy",
        "delisted",
        "wound_down",
        "going_concern",
        "distress_without_failure",
        "unknown",
    ]
    summary: str
    evidence_ids: list[str]
    confidence: str
    verified: bool


class InflectionRead(APIModel):
    id: str
    period: str
    metric: str
    size: float
    explanation: str
    evidence_ids: list[str]


class HypothesisRead(APIModel):
    id: str
    mechanism: str
    supports: list[str]
    contradicts: list[str]
    missing: list[str]
    confidence: str
    critic_notes: str | None = None


class ClaimRead(APIModel):
    id: str
    text: str
    cited_evidence: list[str]
    result: str
    reason: str | None = None


class TimelineResponse(APIModel):
    events: list[EventRead]


class FinancialsResponse(APIModel):
    metrics: list[MetricRead]


class OutcomeResponse(APIModel):
    outcome: OutcomeRead | None


class InflectionsResponse(APIModel):
    inflections: list[InflectionRead]


class HypothesesResponse(APIModel):
    hypotheses: list[HypothesisRead]


class ClaimsResponse(APIModel):
    claims: list[ClaimRead]


class ReportResponse(APIModel):
    report: dict | None


class AssistantMessageRequest(APIModel):
    conversation_id: str | None = None
    text: str = Field(min_length=1, max_length=5_000)
    language: Literal["auto", "en", "hi"] = "auto"


class AssistantFinalEvent(APIModel):
    type: Literal["assistant.final"] = "assistant.final"
    conversation_id: str
    message_id: str
    text: str
    citations: list[str]
    language: str


class TranscriptionResponse(APIModel):
    text: str
    language: str
    duration_ms: int


class SpeechRequest(APIModel):
    message_id: str


class APIError(APIModel):
    code: str
    message: str
