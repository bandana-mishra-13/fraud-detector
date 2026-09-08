"""Test bootstrap: isolate the audit store in a temp SQLite DB and create
tables (in production the FastAPI lifespan does this)."""

import os
import tempfile

# must be set BEFORE any app import — env vars outrank .env files
_TMP = tempfile.mkdtemp(prefix="argus-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test_argus.db"

import pytest  # noqa: E402

from app.store.db import init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    init_db()
