from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import Base
from app.models import Claim, Company, OutcomeAssessment, ResearchRun
from app.providers.base import ProviderResponse
from app.providers.cache import RequestCache
from app.providers.sarvam import SarvamProvider
from app.services.conversation import ConversationService
from app.services.replay import load_replay_case


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _completed_wework_run(db: Session) -> ResearchRun:
    company = Company(legal_name="WeWork Inc.", cik="1533523", ticker="WE", status="demo")
    db.add(company)
    db.commit()
    run = ResearchRun(company_id=company.id, state="queued", node_status={})
    db.add(run)
    db.commit()
    fixture_dir = Path(__file__).resolve().parents[2] / "fixtures"
    assert load_replay_case(db, run, company, fixture_dir)
    db.refresh(run)
    return run


class FixedAnswerProvider:
    """Small reasoning double used to test the server-side response gate."""

    def __init__(self, content: str) -> None:
        self.content = content

    async def complete(self, messages: list[dict[str, str]], **kwargs: object) -> ProviderResponse:
        del messages, kwargs
        return ProviderResponse(content=self.content, metadata={})


def test_replay_loader_preserves_receipts_and_removes_unsupported_claims() -> None:
    db = _session()
    run = _completed_wework_run(db)
    assert run.state == "completed"
    supported = db.scalars(select(Claim).where(Claim.run_id == run.id, Claim.result == "supported")).all()
    unsupported = db.scalars(select(Claim).where(Claim.run_id == run.id, Claim.result == "unsupported")).all()
    assert supported and supported[0].cited_evidence == ["E-001"]
    assert unsupported
    assert run.final_report["verification"]["removed"] == 1


def test_grounded_chat_cites_known_evidence_and_refuses_unrelated_questions() -> None:
    db = _session()
    run = _completed_wework_run(db)
    # Tests must not inherit a developer's real Sarvam key from `.env`.
    settings = Settings(database_url="sqlite:///:memory:", sarvam_api_key=None)
    service = ConversationService(db, settings, SarvamProvider(settings, RequestCache(Path("/tmp"))))

    answer = asyncio.run(
        service.reply(run, conversation_id=None, text="When was the Chapter 11 filing?", language="en")
    )
    assert "[E-001]" in answer.text
    assert answer.citations == ["E-001"]

    unknown = asyncio.run(
        service.reply(run, conversation_id=answer.conversation_id, text="Who will win tomorrow?", language="en")
    )
    assert "cannot confirm" in unknown.text.casefold()
    assert unknown.citations == []


def test_model_reply_requires_a_valid_receipt_on_every_substantive_sentence() -> None:
    db = _session()
    run = _completed_wework_run(db)
    settings = Settings(database_url="sqlite:///:memory:", sarvam_api_key="test-key")
    service = ConversationService(
        db,
        settings,
        FixedAnswerProvider("The filing is documented. [E-001] The chief executive caused the collapse."),  # type: ignore[arg-type]
    )

    answer = asyncio.run(
        service.reply(run, conversation_id=None, text="When was the Chapter 11 filing?", language="en")
    )

    assert "chief executive" not in answer.text.casefold()
    assert answer.citations == ["E-001"]


def test_model_reply_rejects_unknown_receipts_before_storage() -> None:
    db = _session()
    run = _completed_wework_run(db)
    settings = Settings(database_url="sqlite:///:memory:", sarvam_api_key="test-key")
    service = ConversationService(
        db,
        settings,
        FixedAnswerProvider("The filing is documented. [E-999]"),  # type: ignore[arg-type]
    )

    answer = asyncio.run(
        service.reply(run, conversation_id=None, text="When was the Chapter 11 filing?", language="en")
    )

    assert "e-999" not in answer.text.casefold()
    assert answer.citations == ["E-001"]


def test_all_four_replay_cases_preserve_the_survivor_control() -> None:
    db = _session()
    expected = {
        "1533523": "bankruptcy",
        "886158": "bankruptcy",
        "1577967": "bankruptcy",
        "1690820": "distress_without_failure",
    }
    fixture_dir = Path(__file__).resolve().parents[2] / "fixtures"
    for cik, status in expected.items():
        company = Company(legal_name=f"Fixture {cik}", cik=cik, ticker=f"T{cik[-3:]}", status="demo")
        db.add(company)
        db.commit()
        run = ResearchRun(company_id=company.id, state="queued", node_status={})
        db.add(run)
        db.commit()
        assert load_replay_case(db, run, company, fixture_dir)
        outcome = db.scalar(select(OutcomeAssessment).where(OutcomeAssessment.run_id == run.id))
        assert outcome is not None
        assert outcome.status == status
