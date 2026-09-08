from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .store.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # create audit tables if missing (SQLite: also creates the file)
    yield


app = FastAPI(
    title="Argus AML API",
    version="0.3.0",
    description=(
        "Agentic anti-money-laundering analysis. A natural-language query is "
        "parsed into intent + filters, planned into a dynamic tool sequence, "
        "and executed against transaction data — returning explainable, "
        "risk-classified flags with escalation recommendations."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Next.js hops to 3001+ when 3000 is busy — accept any localhost port so
    # a fallback port never breaks the demo with CORS preflight rejections
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Liveness check — the frontend's status pill polls this."""
    return {
        "status": "ok",
        "service": "argus-aml",
        "version": app.version,
        "dataset_present": settings.dataset_available(),
    }


@app.get("/dataset/info")
def dataset_info() -> dict:
    """Dataset summary. First call builds the parquet caches (slow once)."""
    from .data.loader import dataset_info as info

    return info()


class QueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    # optional per-tool manual overrides: {"eda": "on", "ml_anomaly": "off"}.
    # Anything omitted (or "auto") keeps the agent's own decision.
    tool_overrides: dict[str, str] | None = None


@app.post("/query")
def run_query(req: QueryRequest) -> dict:
    """The agent endpoint: NL query in → plan + flags + explanation out.

    Flow: LLM parses intent → planner decides which tools run (and which are
    skipped, with reasons) → optional reviewer overrides → executor runs them
    deterministically → LLM writes the summary. Detection never depends on
    the LLM.
    """
    from .agent.executor import execute
    from .agent.intent import parse_intent
    from .agent.llm import LLMError, RateLimited
    from .agent.overrides import apply_overrides
    from .agent.planner import build_plan
    from .agent.synthesizer import synthesize

    try:
        spec = parse_intent(req.query)
    except RateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # malformed JSON after retry, etc.
        raise HTTPException(
            status_code=502, detail=f"Intent parsing failed: {exc}"
        ) from exc

    planned = apply_overrides(build_plan(spec), req.tool_overrides)
    result = execute(req.query, spec, planned)
    summary, llm_error = synthesize(result)
    result.summary = summary

    payload = result.model_dump(mode="json")
    if llm_error:
        payload["llm_warning"] = llm_error
    return payload
