"""Small database operations that keep route handlers thin."""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Company, Evidence, ResearchRun, Source
from ..providers.sec import DEMO_COMPANIES


def ensure_demo_companies(db: Session) -> list[Company]:
    """Seed only stable demo identities; live lookup remains an optional enhancement."""
    existing = {company.cik: company for company in db.scalars(select(Company)).all() if company.cik}
    created: list[Company] = []
    for item in DEMO_COMPANIES:
        company = existing.get(item["cik"])
        if not company:
            company = Company(**item, status="demo")
            db.add(company)
            created.append(company)
    if created:
        db.commit()
    return db.scalars(select(Company).order_by(Company.legal_name)).all()


def upsert_public_company(db: Session, identity: dict[str, str]) -> Company:
    """Persist a SEC-directory identity so it can be selected for a research run."""

    cik = str(identity["cik"])
    company = db.scalar(select(Company).where(Company.cik == cik))
    if company is None:
        company = Company(
            legal_name=str(identity["legal_name"]),
            cik=cik,
            ticker=str(identity.get("ticker") or "") or None,
            status="public_company",
        )
        db.add(company)
    else:
        company.legal_name = str(identity["legal_name"])
        company.ticker = str(identity.get("ticker") or "") or None
        if company.status != "demo":
            company.status = "public_company"
        db.add(company)
    db.commit()
    db.refresh(company)
    return company


def source_hash(url: str, text: str) -> str:
    return hashlib.sha256(f"{url}\n{text}".encode()).hexdigest()


def next_evidence_key(db: Session, run_id: str) -> str:
    count = len(db.scalars(select(Evidence.id).where(Evidence.run_id == run_id)).all())
    return f"E-{count + 1:03d}"


def add_evidence(
    db: Session,
    *,
    run_id: str,
    url: str,
    text: str,
    source_type: str = "filing",
    title: str | None = None,
    publisher: str | None = None,
    published_at: datetime | None = None,
    quote_start: int | None = None,
    quote_end: int | None = None,
) -> Evidence:
    """Insert a source/chunk pair, preserving a per-run human-readable receipt ID."""
    # A source is a document/URL; chunks beneath it receive their own content hash.
    document_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    source = db.scalar(select(Source).where(Source.run_id == run_id, Source.content_hash == document_hash))
    if not source:
        source = Source(
            run_id=run_id,
            url=url,
            title=title,
            publisher=publisher,
            published_at=published_at,
            source_type=source_type,
            content_hash=document_hash,
        )
        db.add(source)
        db.flush()
    evidence = Evidence(
        run_id=run_id,
        source_id=source.id,
        evidence_key=next_evidence_key(db, run_id),
        text=text,
        quote_start=quote_start,
        quote_end=quote_end,
        content_hash=source_hash(url, text),
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def get_run_or_none(db: Session, run_id: str) -> ResearchRun | None:
    return db.get(ResearchRun, run_id)
