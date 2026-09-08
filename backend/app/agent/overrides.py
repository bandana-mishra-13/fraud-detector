"""Manual tool overrides on top of the agent's plan.

By default the agent decides every tool (Auto). A reviewer may override any
tool to force it on or off — the plan still records the decision AND that a
human made it, so the audit story stays honest ("ran because the operator
required it").

Dependencies are resolved automatically so an override can't produce an
invalid plan: e.g. forcing risk_classification on also forces the detectors
and feature engineering it needs; forcing feature_engineering off also turns
off everything downstream of it.
"""

from .planner import TOOL_ORDER, PlannedStep

# tool -> tools it directly requires (must be invoked before it can run)
_REQUIRES: dict[str, list[str]] = {
    "apply_filters": ["load_data"],
    "eda": ["apply_filters"],
    "feature_engineering": ["apply_filters"],
    "rule_detection": ["feature_engineering"],
    "ml_anomaly": ["feature_engineering"],
    "aggregation": ["apply_filters"],
    "entity_lookup": ["apply_filters"],
    "risk_classification": ["rule_detection"],
}

# tools that can never be turned off — the pipeline is meaningless without them
_LOCKED = {"load_data", "apply_filters"}

# reverse edges: tool -> tools that depend on it
_DEPENDENTS: dict[str, list[str]] = {}
for _t, _deps in _REQUIRES.items():
    for _d in _deps:
        _DEPENDENTS.setdefault(_d, []).append(_t)


def apply_overrides(
    steps: list[PlannedStep], overrides: dict[str, str] | None
) -> list[PlannedStep]:
    """Return a new plan with force-on / force-off overrides applied.

    overrides maps a tool name to "on" or "off". Anything absent (or "auto")
    keeps the agent's decision.
    """
    if not overrides:
        return steps

    decision = {s.tool: s for s in steps}
    forced_on: set[str] = set()
    forced_off: set[str] = set()

    for tool, mode in overrides.items():
        if tool not in decision or mode not in ("on", "off"):
            continue
        if mode == "off" and tool in _LOCKED:
            continue  # cannot disable load_data / apply_filters
        (forced_on if mode == "on" else forced_off).add(tool)

    # forcing a tool ON pulls in everything it requires (transitively)
    def pull_deps(tool: str) -> None:
        for dep in _REQUIRES.get(tool, []):
            if dep not in forced_on:
                forced_on.add(dep)
                pull_deps(dep)

    for tool in list(forced_on):
        pull_deps(tool)

    # forcing a tool OFF cascades to everything that depends on it
    def push_off(tool: str) -> None:
        for dep in _DEPENDENTS.get(tool, []):
            if dep not in forced_off and dep not in _LOCKED:
                forced_off.add(dep)
                push_off(dep)

    for tool in list(forced_off):
        push_off(tool)

    # off wins over on for an explicit conflict on the same tool
    forced_on -= forced_off

    out: list[PlannedStep] = []
    for step in steps:
        if step.tool in forced_on and not step.invoke:
            out.append(
                PlannedStep(step.tool, True, "forced on by reviewer", step.params)
            )
        elif step.tool in forced_off and step.invoke:
            out.append(
                PlannedStep(step.tool, False, "forced off by reviewer", step.params)
            )
        elif step.tool in forced_on and step.invoke and _is_reviewer_choice(step, overrides):
            # already running, but the reviewer explicitly asked for it — note it
            out.append(
                PlannedStep(step.tool, True, f"{step.reason} (kept on by reviewer)", step.params)
            )
        else:
            out.append(step)

    order = {name: i for i, name in enumerate(TOOL_ORDER)}
    out.sort(key=lambda s: order[s.tool])
    return out


def _is_reviewer_choice(step: PlannedStep, overrides: dict[str, str]) -> bool:
    return overrides.get(step.tool) == "on"
