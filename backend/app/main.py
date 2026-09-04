import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.health import router as health_router
from app.storage import get_audit_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure local data and storage directories exist on startup
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    # Initialize SQLite audit database schema and tables
    audit_store = get_audit_store()
    audit_store.init_db()
    yield


app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    version=settings.VERSION,
    description="Agentic AML & Financial Crime Detection Platform API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register health check at root /health and under API prefix
app.include_router(health_router)
app.include_router(health_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs": "/docs",
        "health": "/health",
        "version": settings.VERSION,
    }
