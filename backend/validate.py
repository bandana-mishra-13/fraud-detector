"""Validate Argus detectors against IBM's labeled laundering attempts.

Parses HI-Small_Patterns.txt (370 labeled typology attempts), runs the full
hybrid detection stack on the analysis sample, and reports:

- per-typology attempt detection rate (≥1 involved account flagged)
- precision@K against label-involved accounts
- flag volume (false-positive pressure)

Usage:
  .venv/bin/python validate.py             # current DEFAULT_THRESHOLDS
  .venv/bin/python validate.py --candidate # candidate threshold set
"""

import re
import sys
from collections import defaultdict

from app.config import settings
from app.data.loader import load_sample
from app.tools.detectors import DEFAULT_THRESHOLDS, run_isolation_forest, run_rules
from app.tools.features import build_features
from app.tools.risk import classify

CANDIDATE_THRESHOLDS = {
    # loosen smurfing (0 hits at baseline on real data)
    "smurfing_min_txns": 5,
    "smurfing_min_senders": 3,
    # tighten the noisy rules — moderate point between baseline and the
    # aggressive first candidate (which cost 4pts of typology coverage)
    "layering_min_volume": 75_000.0,
    "layering_min_passthrough": 0.82,
    "cashout_min_ratio": 0.55,
    "cashout_min_inflow": 30_000.0,
    "velocity_min_txns_24h": 30,
}

FAMILY_RE = re.compile(r"BEGIN LAUNDERING ATTEMPT - ([A-Z-]+)")


def parse_patterns(path) -> list[tuple[str, set[str]]]:
    """→ [(family, involved_accounts), ...] for each labeled attempt."""
    attempts = []
    family, accounts = None, set()
    with open(path) as fh:
        for line in fh:
            m = FAMILY_RE.search(line)
            if m:
                family, accounts = m.group(1), set()
            elif line.startswith("END LAUNDERING ATTEMPT"):
                if family and accounts:
                    attempts.append((family, accounts))
                family = None
            elif family and "," in line:
                parts = line.split(",")
                if len(parts) >= 5:
                    accounts.add(parts[2])
                    accounts.add(parts[4])
    return attempts


def main() -> None:
    use_candidate = "--candidate" in sys.argv
    thresholds = {**DEFAULT_THRESHOLDS, **CANDIDATE_THRESHOLDS} if use_candidate else None
    label = "CANDIDATE" if use_candidate else "BASELINE (DEFAULT_THRESHOLDS)"

    patterns_path = settings.patterns_path
    attempts = parse_patterns(patterns_path)
    print(f"labeled attempts: {len(attempts)}\n")

    df = load_sample()
    feats = build_features(df)
    signals = run_rules(df, feats, thresholds=thresholds)
    ml = run_isolation_forest(feats)
    flags = classify(signals, ml, top_n=100_000)

    flagged = {f.entity_id for f in flags}
    flag_order = [f.entity_id for f in flags]  # strongest first

    hot = set()
    for _, accts in attempts:
        hot |= accts

    # per-typology attempt detection rate
    per_family: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for family, accts in attempts:
        per_family[family][1] += 1
        if accts & flagged:
            per_family[family][0] += 1

    print(f"== {label} ==")
    print(f"total flags: {len(flags):,}  ({len(flagged):,} accounts)")
    for k in (50, 100):
        top = flag_order[:k]
        hits = sum(1 for a in top if a in hot)
        print(f"precision@{k} vs attempt-involved accounts: {hits}/{k} = {hits / k:.0%}")
    caught = sum(v[0] for v in per_family.values())
    total = sum(v[1] for v in per_family.values())
    print(f"attempts with >=1 flagged account: {caught}/{total} = {caught / total:.0%}\n")
    print(f"{'typology':<16}{'caught':>8}{'total':>8}{'rate':>8}")
    for family in sorted(per_family):
        c, t = per_family[family]
        print(f"{family:<16}{c:>8}{t:>8}{c / t:>8.0%}")

    from collections import Counter

    print("\nflag volume by pattern:", dict(Counter(f.pattern.value for f in flags)))


if __name__ == "__main__":
    main()
