from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models import Company
from ..providers.base import ProviderError
from ..providers.cache import RequestCache
from ..providers.sec import SecProvider
from ..schemas import CompanyRead, CompanySearchResponse
from ..services.repository import ensure_demo_companies, upsert_public_company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/search", response_model=CompanySearchResponse)
async def search_companies(
    q: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CompanySearchResponse:
    ensure_demo_companies(db)
    pattern = f"%{q.strip()}%"
    results = db.scalars(
        select(Company)
        .where(or_(Company.legal_name.ilike(pattern), Company.ticker.ilike(pattern), Company.cik.ilike(pattern)))
        .order_by(Company.legal_name)
        .limit(10)
    ).all()
    if results or settings.is_replay:
        return CompanySearchResponse(results=[CompanyRead.model_validate(company) for company in results])

    provider = SecProvider(settings, RequestCache(settings.fixture_path, settings.demo_mode))
    try:
        identities = await provider.search(q, limit=10)
    except ProviderError:
        # A temporary SEC lookup issue should leave the picker empty, not expose a
        # raw upstream failure or invent a company identity.
        return CompanySearchResponse(results=[])
    companies = [upsert_public_company(db, identity) for identity in identities]
    return CompanySearchResponse(results=[CompanyRead.model_validate(company) for company in companies])
