"""Dynamic Execution Planner (Task 3.2).

Transforms a ParsedIntent or raw query into an ordered, executable ExecutionPlan.
Dynamically decides which tools to invoke and which tools to skip with clear rationale.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from app.agent.intent_parser import parse_intent, parse_intent_async
from app.models.schemas import (
    ExecutionPlan,
    IntentType,
    ParsedIntent,
    PlanStep,
    SkippedTool,
    StepStatus,
)


def _build_active_filters(parsed_intent: ParsedIntent) -> Dict[str, Any]:
    """Extract and consolidate active filters and temporal constraints."""
    filters = dict(parsed_intent.filters) if parsed_intent.filters else {}

    if parsed_intent.time_window:
        tw = parsed_intent.time_window
        if tw.raw_text:
            filters["time_window"] = tw.raw_text
        if tw.value is not None and tw.unit is not None:
            filters[f"time_window_{tw.unit}"] = tw.value
            if tw.unit == "days":
                filters["time_window_days"] = tw.value
            elif tw.unit == "hours":
                filters["time_window_hours"] = tw.value
            elif tw.unit == "weeks":
                filters["time_window_days"] = tw.value * 7
            elif tw.unit == "months":
                filters["time_window_days"] = tw.value * 30
        if tw.start_date:
            filters["start_date"] = tw.start_date
        if tw.end_date:
            filters["end_date"] = tw.end_date

    if parsed_intent.pattern:
        filters["pattern"] = parsed_intent.pattern

    return filters


def create_execution_plan(intent_or_query: Union[ParsedIntent, str]) -> ExecutionPlan:
    """Synchronously generate an ExecutionPlan from a ParsedIntent or raw query string."""
    if isinstance(intent_or_query, str):
        parsed = parse_intent(intent_or_query)
    elif isinstance(intent_or_query, ParsedIntent):
        parsed = intent_or_query
    else:
        raise TypeError(f"Expected ParsedIntent or str, got {type(intent_or_query)}")

    return _synthesize_plan(parsed)


async def create_execution_plan_async(intent_or_query: Union[ParsedIntent, str]) -> ExecutionPlan:
    """Asynchronously generate an ExecutionPlan from a ParsedIntent or raw query string."""
    if isinstance(intent_or_query, str):
        parsed = await parse_intent_async(intent_or_query)
    elif isinstance(intent_or_query, ParsedIntent):
        parsed = intent_or_query
    else:
        raise TypeError(f"Expected ParsedIntent or str, got {type(intent_or_query)}")

    return _synthesize_plan(parsed)


def _synthesize_plan(parsed: ParsedIntent) -> ExecutionPlan:
    """Construct dynamic plan steps, skipped tools, and reasoning based on intent."""
    plan_id = str(uuid.uuid4())
    intent_type = parsed.intent
    active_filters = _build_active_filters(parsed)
    target_entities = list(parsed.entities)

    steps: List[PlanStep] = []
    invoked_tools: List[str] = []
    skipped_tools: List[SkippedTool] = []
    reasoning: str = ""

    if intent_type == IntentType.BROAD_ANALYSIS:
        # Archetype 1: Full dataset scan (EDA -> Features -> ML -> Rules -> Risk -> Explain)
        steps = [
            PlanStep(
                step_number=1,
                tool_name="eda",
                description="Generate exploratory data analysis, transaction counts, volume distributions, and counterparty summaries.",
                parameters={},
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=2,
                tool_name="features",
                description="Engineer rolling transaction velocities, sub-$10k counts, and network graph degrees.",
                parameters={},
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=3,
                tool_name="detectors_ml",
                description="Execute Isolation Forest anomaly detector on engineered feature set to compute statistical anomaly scores.",
                parameters={"contamination": 0.05},
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=4,
                tool_name="detectors_rules",
                description="Evaluate deterministic AML rule detectors (structuring, smurfing, rapid layering, fan-out, velocity).",
                parameters={},
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=5,
                tool_name="risk",
                description="Fuse deterministic rule flags with ML anomaly scores into normalized risk scores and categorical tiers.",
                parameters={},
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=6,
                tool_name="explain",
                description="Generate natural language explainability narratives and evidence citations for all flagged findings.",
                parameters={},
                status=StepStatus.PENDING,
            ),
        ]
        invoked_tools = ["eda", "features", "detectors_ml", "detectors_rules", "risk", "explain"]
        skipped_tools = []
        reasoning = (
            "Full end-to-end AML investigative pipeline scheduled: baseline EDA profiling, "
            "rolling feature engineering, Isolation Forest unsupervised anomaly detection, "
            "comprehensive deterministic AML rule evaluation, hybrid risk score fusion, and compliance explainability."
        )

    elif intent_type == IntentType.PATTERN_DETECTION:
        # Archetype 2: Targeted typology search with optional temporal filter
        # Skips EDA and ML (e.g., "Find structuring patterns in the last 30 days")
        pattern = parsed.pattern or "structuring"
        rule_params: Dict[str, Any] = {"rules": [pattern]}
        rule_params.update(active_filters)

        steps = [
            PlanStep(
                step_number=1,
                tool_name="detectors_rules",
                description=f"Execute deterministic AML detector for '{pattern}' typology with active temporal and threshold filters.",
                parameters=rule_params,
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=2,
                tool_name="risk",
                description="Calculate risk severity and tier categorization for detected typology flags.",
                parameters={},
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=3,
                tool_name="explain",
                description="Synthesize typology-specific investigative explanations citing supporting transactions.",
                parameters={},
                status=StepStatus.PENDING,
            ),
        ]
        invoked_tools = ["detectors_rules", "risk", "explain"]
        skipped_tools = [
            SkippedTool(
                tool_name="eda",
                reason="EDA skipped: Query targets a specific typology pattern with temporal constraints rather than overall baseline profiling.",
            ),
            SkippedTool(
                tool_name="detectors_ml",
                reason="ML Anomaly Detection skipped: Query specifically searches for deterministic rule-based typology patterns where thresholds are strictly defined.",
            ),
            SkippedTool(
                tool_name="features",
                reason="Feature engineering skipped: Deterministic rule detector operates directly on filtered transaction time series.",
            ),
        ]
        reasoning = (
            f"Targeted rule investigation plan generated for '{pattern}' typology with temporal/threshold constraints. "
            "Unsupervised ML and exploratory profiling are bypassed to minimize latency and focus execution on deterministic rule evaluation."
        )

    elif intent_type == IntentType.AGGREGATION:
        # Archetype 3: Pure aggregation and threshold filtering
        # Skips ML (e.g., "Which customers made 10+ transactions under $10,000?")
        steps = [
            PlanStep(
                step_number=1,
                tool_name="features",
                description="Calculate transaction frequencies, aggregated volumes, and threshold counts per account.",
                parameters=active_filters,
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=2,
                tool_name="detectors_rules",
                description="Apply threshold rules and identify candidate accounts matching aggregation criteria.",
                parameters={"rules": ["structuring", "velocity"], **active_filters},
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=3,
                tool_name="risk",
                description="Assess risk scores and tier categorizations for accounts meeting aggregation criteria.",
                parameters={},
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=4,
                tool_name="explain",
                description="Generate findings breakdown and transaction evidence citations for matching entities.",
                parameters={},
                status=StepStatus.PENDING,
            ),
        ]
        invoked_tools = ["features", "detectors_rules", "risk", "explain"]
        skipped_tools = [
            SkippedTool(
                tool_name="detectors_ml",
                reason="ML Anomaly Detection skipped: Query requires deterministic aggregation and exact threshold counting; unsupervised ML is not applicable.",
            ),
            SkippedTool(
                tool_name="eda",
                reason="Global EDA skipped: Aggregation analysis directly evaluates entity transaction frequencies and threshold criteria.",
            ),
        ]
        reasoning = (
            "Deterministic aggregation pipeline scheduled to compute account-level transaction counts and amount threshold filters. "
            "Machine learning anomaly scoring is skipped as the query specifies exact deterministic filter criteria."
        )

    elif intent_type == IntentType.ENTITY_INVESTIGATION:
        # Archetype 4: Single entity 360° investigation (e.g., "Is customer 4521 suspicious?")
        target_entity = target_entities[0] if target_entities else "target_entity"
        entity_params: Dict[str, Any] = {"entity_id": target_entity}

        steps = [
            PlanStep(
                step_number=1,
                tool_name="eda",
                description=f"Profile transaction volume, flow distribution, and top counterparties for entity {target_entity}.",
                parameters=entity_params,
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=2,
                tool_name="features",
                description=f"Compute rolling velocities and graph degree metrics for entity {target_entity}.",
                parameters=entity_params,
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=3,
                tool_name="detectors_rules",
                description=f"Evaluate all deterministic AML rules for entity {target_entity}.",
                parameters=entity_params,
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=4,
                tool_name="detectors_ml",
                description=f"Calculate ML anomaly score for entity {target_entity}.",
                parameters=entity_params,
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=5,
                tool_name="risk",
                description=f"Fuse rule flags and ML anomaly score into comprehensive 360° risk evaluation for entity {target_entity}.",
                parameters=entity_params,
                status=StepStatus.PENDING,
            ),
            PlanStep(
                step_number=6,
                tool_name="explain",
                description=f"Generate natural language investigative breakdown and evidence summary for entity {target_entity}.",
                parameters=entity_params,
                status=StepStatus.PENDING,
            ),
        ]
        invoked_tools = ["eda", "features", "detectors_rules", "detectors_ml", "risk", "explain"]
        skipped_tools = []
        reasoning = (
            f"Targeted 360° entity drill-down plan generated for entity {target_entity}. "
            "Combines entity-level profiling, feature metrics, rule evaluation, ML anomaly scoring, hybrid risk fusion, and evidence citations."
        )

    else:
        # Unsupported or unclassifiable intent
        steps = []
        invoked_tools = []
        skipped_tools = [
            SkippedTool(
                tool_name="all_tools",
                reason="Query does not correspond to a supported AML financial crime investigation objective.",
            )
        ]
        reasoning = "No analytical tools scheduled because the user query is outside the scope of AML financial crime detection."

    return ExecutionPlan(
        plan_id=plan_id,
        query=parsed.query,
        detected_intent=intent_type.value if hasattr(intent_type, "value") else str(intent_type),
        active_filters=active_filters,
        target_entities=target_entities,
        steps=steps,
        invoked_tools=invoked_tools,
        skipped_tools=skipped_tools,
        reasoning=reasoning,
        created_at=datetime.now(timezone.utc),
    )
