"""Database engine/session, driven entirely by DATABASE_URL.

SQLite by default (zero-setup for local runs and judges); swap the env var to
a Postgres URL for production — no code change.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..config import settings


class Base(DeclarativeBase):
    pass


_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables if missing — called on app startup."""
    from . import audit  # noqa: F401  (register models with Base.metadata)

    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
