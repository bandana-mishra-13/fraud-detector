"""Executor: run the planned steps, collect results, record the trace.

Deterministic by construction — the LLM chose WHAT to run (via the spec);
here only tools run. Same spec + same data → same flags, always.
"""

import time
from collections import Counter

import pandas as pd

from ..data.loader import load_accounts, load_sample
from ..models.schemas import ExecutionPlan, Flag, PlanStep, QueryFilters, RiskResult
from ..store.audit import flags_for_entity, record_run
from ..tools.detectors import population_anomaly_scores, run_rules
from ..tools.eda import run_eda
from ..tools.features import build_features
from ..tools.filters import apply_filters, resolve_customer_accounts
from ..tools.risk import classify
from .intent import IntentSpec
from .planner import PlannedStep


AGGREGATION_DISPLAY_LIMIT = 250


def _aggregation(
    df: pd.DataFrame, accounts: pd.DataFrame, params: dict
) -> tuple[list[dict], int]:
    """Direct threshold aggregation: accounts with >= N txns under $X.

    Returns (rows_for_display, total_matches) — the total is the honest answer
    to "how many customers match", independent of the display cap.
    """
    scope = df
    if params.get("max_amount"):
        scope = scope[scope["amount_paid"] < params["max_amount"]]
    if params.get("min_amount"):
        scope = scope[scope["amount_paid"] >= params["min_amount"]]
    grouped = (
        scope.groupby("from_account", observed=True)["amount_paid"]
        .agg(txn_count="count", total="sum")
        .reset_index()
    )
    hits = grouped[grouped["txn_count"] >= params.get("min_txn_count", 10)]
    total = int(len(hits))
    hits = hits.nlargest(AGGREGATION_DISPLAY_LIMIT, "txn_count")
    directory = accounts.set_index("account")["entity_name"]
    rows = [
        {
            "account": str(r.from_account),
            "customer": str(directory.get(r.from_account, "unknown")),
            "txn_count": int(r.txn_count),
            "total": round(float(r.total), 2),
        }
        for r in hits.itertuples()
    ]
    return rows, total


def execute(
    query: str,
    spec: IntentSpec,
    planned: list[PlannedStep],
    df: pd.DataFrame | None = None,
    accounts: pd.DataFrame | None = None,
) -> RiskResult:
    t_start = time.time()
    steps_out: list[PlanStep] = []
    ctx: dict = {}

    def run_step(step: PlannedStep) -> None:
        if not step.invoke:
            steps_out.append(
                PlanStep(tool=step.tool, action="skipped", reason=step.reason, params=step.params)
            )
            return
        t0 = time.time()
        _dispatch(step)
        steps_out.append(
            PlanStep(
                tool=step.tool,
                action="invoked",
                reason=step.reason,
                params=step.params,
                duration_ms=int((time.time() - t0) * 1000),
            )
        )

    def _dispatch(step: PlannedStep) -> None:
        if step.tool == "load_data":
            ctx["df"] = df if df is not None else load_sample()
            ctx["accounts"] = accounts if accounts is not None else load_accounts()
        elif step.tool == "apply_filters":
            ctx["slice"], ctx["filters_applied"] = apply_filters(
                ctx["df"], spec.filters, ctx["accounts"]
            )
        elif step.tool == "eda":
            ctx["eda"] = run_eda(ctx["slice"])
        elif step.tool == "feature_engineering":
            ctx["features"] = build_features(ctx["slice"])
        elif step.tool == "rule_detection":
            ctx["signals"] = run_rules(
                ctx["slice"], ctx["features"], patterns=step.params.get("patterns")
            )
        elif step.tool == "ml_anomaly":
            # population-fit scores (cached): same account → same score on
            # every query; candidates restricted to the query's slice
            scores = population_anomaly_scores(ctx["df"])
            slice_accounts = pd.unique(
                pd.concat(
                    [ctx["slice"]["from_account"], ctx["slice"]["to_account"]],
                    ignore_index=True,
                )
            )
            ctx["ml_scores"] = scores[scores.index.isin(slice_accounts)]
        elif step.tool == "aggregation":
            rows, total = _aggregation(ctx["slice"], ctx["accounts"], step.params)
            ctx["aggregation"], ctx["aggregation_total"] = rows, total
        elif step.tool == "entity_lookup":
            ids: list[str] = []
            if spec.filters.account:
                ids = [spec.filters.account]
            elif spec.filters.customer:
                ids = resolve_customer_accounts(spec.filters.customer, ctx["accounts"])
            ctx["entity_accounts"] = ids
            ctx["prior_flags"] = [
                {
                    "entity_id": fl.entity_id,
                    "pattern": fl.pattern,
                    "risk_level": fl.risk_level,
                    "reason": fl.reason,
                    "flagged_at": str(fl.created_at),
                }
                for a in ids
                for fl in flags_for_entity(a)
            ]
        elif step.tool == "risk_classification":
            # classify everything, then truncate for transport — the KPIs must
            # report what was actually FOUND, not the display cap.
            all_flags = classify(
                ctx.get("signals", []), ctx.get("ml_scores"), top_n=10**9
            )
            ctx["all_flags"] = all_flags
            ctx["flags"] = all_flags[: spec.top_n]

    for step in planned:
        run_step(step)

    flags: list[Flag] = ctx.get("flags", [])
    all_flags: list[Flag] = ctx.get("all_flags", flags)

    # KPIs for the workbench strip — totals are the true counts across the
    # whole analysed slice; *_shown is how many were returned for display.
    slice_df = ctx.get("slice", ctx.get("df"))
    kpis = {
        "transactions_scanned": int(len(slice_df)) if slice_df is not None else 0,
        "flags_raised": len(all_flags),
        "flags_shown": len(flags),
        "high_risk": sum(1 for f in all_flags if f.risk_level.value == "high"),
        "elapsed_ms": int((time.time() - t_start) * 1000),
    }
    if ctx.get("aggregation") is not None:
        kpis["aggregation_matches"] = ctx.get("aggregation_total", len(ctx["aggregation"]))
        kpis["aggregation_shown"] = len(ctx["aggregation"])

    charts: dict = {}
    if "eda" in ctx:
        charts.update(ctx["eda"]["charts"])
        kpis["eda_summary"] = {
            k: v for k, v in ctx["eda"].items() if k not in ("charts",)
        }
    if flags:
        level_counts = Counter(f.risk_level.value for f in flags)
        charts["risk_breakdown"] = [
            {"level": lvl, "count": level_counts.get(lvl, 0)}
            for lvl in ("high", "medium", "low")
        ]
    if ctx.get("aggregation") is not None:
        charts["aggregation_table"] = ctx["aggregation"]
    if ctx.get("prior_flags") is not None:
        charts["prior_flags"] = ctx["prior_flags"]
        charts["entity_accounts"] = ctx.get("entity_accounts", [])

    plan = ExecutionPlan(
        query=query,
        intent=spec.intent,
        pattern=spec.pattern,
        filters=spec.filters,
        steps=steps_out,
    )
    run_id = record_run(plan, flags)
    return RiskResult(run_id=run_id, plan=plan, flags=flags, kpis=kpis, charts=charts)
