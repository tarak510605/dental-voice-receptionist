"""
Health-check router.
GET /health — used by load-balancers, deployment platforms, and uptime monitors.
"""

from fastapi import APIRouter
from app.config.settings import get_settings
from app.schemas.booking import HealthResponse

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns service health status. Always responds 200 if the process is alive.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        service=settings.APP_NAME,
    )
