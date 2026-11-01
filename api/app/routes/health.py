from fastapi import APIRouter, Depends

from ..config import Settings, get_settings
from ..schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(service=settings.app_name, environment=settings.environment, demo_mode=settings.demo_mode)
