"""Planner: IntentSpec → dynamic execution plan.

This is the problem statement's core demand made concrete: the agent must NOT
run a fixed pipeline. For every query the planner walks the full tool
universe and decides — invoke or skip — with a stated reason. Skipped tools
stay in the plan so a reviewer can see the decision, not just its absence.
"""

from dataclasses import dataclass, field

from .intent import IntentSpec

# the full tool universe, in canonical execution order
TOOL_ORDER = [
    "load_data",
    "apply_filters",
    "eda",
    "feature_engineering",
    "rule_detection",
    "ml_anomaly",
    "aggregation",
    "entity_lookup",
    "risk_classification",
]


@dataclass
class PlannedStep:
    tool: str
    invoke: bool
    reason: str
    params: dict = field(default_factory=dict)


def build_plan(spec: IntentSpec) -> list[PlannedStep]:
    f = spec.filters
    has_filters = any(
        v is not None and v != ""
        for v in (
            f.last_n_days, f.date_from, f.date_to, f.min_amount, f.max_amount,
            f.currency, f.payment_format, f.bank, f.account, f.customer,
        )
    )
    steps: list[PlannedStep] = [
        PlannedStep("load_data", True, "dataset sample required for any analysis"),
        PlannedStep(
            "apply_filters",
            True,
            "narrowing to the query's slice" if has_filters
            else "no filters extracted — full sample in scope",
        ),
    ]

    if spec.intent == "full_analysis":
        steps += [
            PlannedStep("eda", True, "broad sweep — baseline profiling informs the reviewer"),
            PlannedStep("feature_engineering", True, "behaviour features feed rules and ML"),
            PlannedStep("rule_detection", True, "all typology rules in scope", {"patterns": None}),
            PlannedStep("ml_anomaly", True, "unsupervised scoring corroborates rules and catches un-named patterns"),
            PlannedStep("aggregation", False, "no count/threshold question asked"),
            PlannedStep("entity_lookup", False, "no single entity named"),
            PlannedStep("risk_classification", True, "convert signals into risk levels and escalations"),
        ]

    elif spec.intent == "pattern_search":
        pattern = spec.pattern.value if spec.pattern else None
        steps += [
            PlannedStep("eda", False, "targeted pattern query — full EDA unnecessary"),
            PlannedStep("feature_engineering", True, f"features required by the {pattern or 'requested'} detector"),
            PlannedStep("rule_detection", True, f"only the {pattern or 'requested'} rule runs", {"patterns": [pattern] if pattern else None}),
            PlannedStep("ml_anomaly", True, "anomaly score corroborates the rule hits"),
            PlannedStep("aggregation", False, "not an aggregation question"),
            PlannedStep("entity_lookup", False, "no single entity named"),
            PlannedStep("risk_classification", True, "classify and rank the pattern hits"),
        ]

    elif spec.intent == "aggregation":
        steps += [
            PlannedStep("eda", False, "aggregation question — no broad exploration needed"),
            PlannedStep("feature_engineering", False, "simple count/threshold aggregation — the full feature set is unnecessary"),
            PlannedStep("rule_detection", False, "the threshold IS the question — typology rules not required"),
            PlannedStep("ml_anomaly", False, "ML anomaly detection is not required for a direct aggregation"),
            PlannedStep(
                "aggregation", True, "direct group-and-threshold answers the question",
                {"min_txn_count": f.min_txn_count or 10, "max_amount": f.max_amount, "min_amount": f.min_amount},
            ),
            PlannedStep("entity_lookup", False, "no single entity named"),
            PlannedStep("risk_classification", False, "no detection signals to classify"),
        ]

    elif spec.intent == "entity_lookup":
        steps += [
            PlannedStep("eda", False, "single-entity question — dataset-wide EDA skipped"),
            PlannedStep("feature_engineering", True, "features computed on the entity's slice only"),
            PlannedStep("rule_detection", True, "typology rules on the entity's transactions"),
            PlannedStep("ml_anomaly", False, "population-scale anomaly model unnecessary for one entity"),
            PlannedStep("aggregation", False, "not an aggregation question"),
            PlannedStep("entity_lookup", True, "resolve the entity and pull existing audit flags", {"customer": f.customer, "account": f.account}),
            PlannedStep("risk_classification", True, "compute on-demand risk for this entity"),
        ]

    else:  # eda_only
        steps += [
            PlannedStep("eda", True, "profiling is the request"),
            PlannedStep("feature_engineering", False, "no detection requested"),
            PlannedStep("rule_detection", False, "no detection requested"),
            PlannedStep("ml_anomaly", False, "no detection requested"),
            PlannedStep("aggregation", False, "not an aggregation question"),
            PlannedStep("entity_lookup", False, "no single entity named"),
            PlannedStep("risk_classification", False, "nothing to classify"),
        ]

    order = {name: i for i, name in enumerate(TOOL_ORDER)}
    steps.sort(key=lambda s: order[s.tool])
    return steps
