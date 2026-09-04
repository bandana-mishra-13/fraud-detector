"""API routers package."""

from app.api.audit import router as audit_router
from app.api.health import router as health_router
from app.api.query import router as query_router

__all__ = [
    "audit_router",
    "health_router",
    "query_router",
]
