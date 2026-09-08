"""Live end-to-end check: the 4 demo queries through /query (real LLM)."""

import time

import httpx

BASE = "http://localhost:8000"
QUERIES = [
    "Analyse this dataset for suspicious activity",
    "Find structuring patterns in the last 30 days",
    "Which customers made 10+ transactions under $10,000?",
    "Is customer 4521 suspicious?",
]

for q in QUERIES:
    print("=" * 78)
    print(f"QUERY: {q}")
    t0 = time.time()
    r = httpx.post(f"{BASE}/query", json={"query": q}, timeout=300.0)
    dt = time.time() - t0
    if r.status_code != 200:
        print(f"  !! HTTP {r.status_code}: {r.text[:300]}")
        continue
    body = r.json()
    plan = body["plan"]
    print(f"  intent: {plan['intent']}  pattern: {plan.get('pattern')}  ({dt:.1f}s)")
    active = {
        k: v for k, v in plan["filters"].items() if v not in (None, "", [])
    }
    print(f"  filters: {active}")
    line = "  plan: " + "  ".join(
        ("[x] " if s["action"] == "invoked" else "[ ] ") + s["tool"]
        for s in plan["steps"]
    )
    print(line)
    print(f"  kpis: {body['kpis']}")
    if body["flags"]:
        f = body["flags"][0]
        print(f"  top flag [{f['risk_level']} · {f['pattern']} · {f['score']}]:")
        print(f"    {f['reason'][:150]}")
    if body["charts"].get("aggregation_table"):
        row = body["charts"]["aggregation_table"][0]
        print(f"  top aggregation row: {row}")
    if body["charts"].get("entity_accounts") is not None:
        print(f"  entity accounts: {body['charts']['entity_accounts'][:3]}")
    print(f"  summary: {body['summary'][:220]}")
    if body.get("llm_warning"):
        print(f"  [!] LLM WARNING: {body['llm_warning']}")
print("=" * 78)
