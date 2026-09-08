"""Explanation Component — plain-English, typology-tied reasons for flags.

Templated from the rule evidence, so every explanation states the concrete
behaviour that triggered the flag (auditable, reproducible). The agent's LLM
may later paraphrase these for the summary, but the reason of record is this.
"""


def _money(x: float | int) -> str:
    return f"${x:,.0f}"


def explain_flag(pattern: str, account: str, ev: dict) -> str:
    if pattern == "structuring":
        n = ev.get("sub_threshold_txns_in_window", 0)
        total = ev.get("window_total", 0)
        window = str(ev.get("window", "7D")).replace("D", " days")
        lo, hi = ev.get("band", (8_500, 10_000))
        return (
            f"Account {account} made {n} payments of {_money(lo)}–{_money(hi)} "
            f"(just under the {_money(hi)} reporting threshold) totalling "
            f"{_money(total)} within {window} — a pattern consistent with "
            f"structuring to evade transaction reporting."
        )

    if pattern == "smurfing":
        n = ev.get("sub_threshold_inbound_txns", 0)
        senders = ev.get("distinct_senders", 0)
        return (
            f"Account {account} received {n} sub-threshold payments from "
            f"{senders} distinct senders — the aggregation side of a "
            f"smurfing scheme, where mules split value to stay under "
            f"reporting limits."
        )

    if pattern == "layering":
        ratio = ev.get("passthrough_24h_ratio", 0)
        inflow = ev.get("inflow_total", 0)
        fan_in = ev.get("fan_in", 0)
        fan_out = ev.get("fan_out", 0)
        return (
            f"Account {account} moved {ratio:.0%} of {_money(inflow)} received "
            f"onward within 24 hours, with {fan_in} inbound and {fan_out} "
            f"outbound counterparties — behaviour typical of a layering "
            f"intermediary obscuring the money trail."
        )

    if pattern == "rapid_cash_out":
        ratio = ev.get("cash_out_within_24h_ratio", 0)
        inflow = ev.get("inflow_total", 0)
        return (
            f"Account {account} converted {ratio:.0%} of {_money(inflow)} in "
            f"inbound funds to cash within 24 hours of receipt — rapid "
            f"cash-out is a classic exit step for laundered value."
        )

    if pattern == "velocity":
        n = ev.get("max_txns_in_24h", 0)
        return (
            f"Account {account} executed {n} transactions inside a single "
            f"24-hour window — a burst far above normal account behaviour."
        )

    # ML-only anomaly (no named typology)
    score = ev.get("ml_anomaly_score", 0)
    return (
        f"Account {account}'s overall behaviour is a strong statistical "
        f"outlier (anomaly score {score:.2f} / 1.00) versus the population — "
        f"no single typology rule fired, which is itself worth review."
    )
