from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    service: str = Field(..., examples=["Argus AML Backend"])
    version: str = Field(..., examples=["0.1.0"])
    timestamp: str = Field(..., examples=["2026-09-02T16:30:00Z"])
    environment: str = Field(default="development", examples=["development"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify backend service operational status.
    Used by frontend status indicators and orchestration health probes.
    """
    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment="development",
    )
