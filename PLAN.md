# Argus AML — Build Plan (48h Hackathon, 3-person team)

This is the human-order build plan: what to do, in what sequence, and who owns
each slice. Three full-stack developers, split by **vertical feature slices** so all
three people's commits are visible across backend, agent/ML, and frontend.

- **Dev A**, **Dev B**, and **Dev C** — swap the labels to your real names/GitHub handles.
- Each numbered item = roughly one commit (or a small cluster of commits).
- Commit frequently, in your own name. Never squash the whole thing into one commit.
- Keep interface contracts (schemas, API routes, tool signatures) strictly agreed upon so you can develop in parallel.

---

## Developer Role Overviews & Vertical Slices

| Developer | Primary Ownership Areas | Core Stack / Touchpoints |
|-----------|-------------------------|--------------------------|
| **Dev A** (Agent & Explainability Lead) | Schemas, EDA Profiling, Intent Parser, LLM Synthesizer, Explainability Engine, Execution Plan UI | Python / FastAPI / Pydantic / OpenRouter / Next.js Plan & Evidence UI |
| **Dev B** (Rules, Risk & Platform Lead) | Backend Setup, Rule Detectors, Risk Fusion Engine, Audit Store, API Endpoints, Core Dashboard UI | FastAPI / SQLite / AML Rule Engine / Next.js Query & Results UI |
| **Dev C** (Data, ML & Analytics Lead) | Data Pipeline & Sampler, Feature Engineering, Isolation Forest ML, Plan Executor & Tracing, Charts & Drill-Down UI | Pandas / Scikit-Learn / Telemetry / Recharts / Next.js Analytics |

---

## Ground rules (from the hackathon doc)

- Public GitHub repo, **frequent commits**, runnable with setup steps.
- **No "SG / Societe Generale / SocGen / SGGSC"** references anywhere. Keep generic.
- README must cite dataset + sources and disclose all tools/APIs/AI assistance.
- Scope: batch analysis on a **sample** is fine. Simplicity + explainability +
  a working end-to-end demo beats model complexity.
- Deliverables: repo + README + max-2-slide deck + 2-min video demo.

---

## Phase 0 — Foundations (All 3, ~first 2h)

| # | Task | Owner |
|---|------|-------|
| 0.1 | ✅ Repo scaffold + README + .gitignore | Done |
| 0.2 | GitHub repository management, push `main`, add teammates as collaborators, branch protection | Dev A |
| 0.3 | Backend: Python venv (3.12), `requirements.txt`, FastAPI `/health` endpoint & app structure | Dev B |
| 0.4 | Frontend: `create-next-app`, Tailwind/CSS theme setup, base layout, `/health` connection | Dev B |
| 0.5 | Data setup: IBM AML `HI-Small_Trans.csv` in `backend/data/` (gitignored) + synthetic mini sample | Dev C |
| 0.6 | `.env.example` + OpenRouter API key wiring & client config (keys stay local, never committed) | Dev C |

**Milestone:** Frontend loads, hits backend health check, dataset ready on disk, OpenRouter connectivity verified.

---

## Phase 1 — Data Layer & Core Schemas (All 3, ~3h)

| # | Task | Owner |
|---|------|-------|
| 1.1 | Pydantic schemas: `Transaction`, `Flag`, `ExecutionPlan`, `RiskResult`, `ExecutionTrace` | Dev A |
| 1.2 | Data loader: read CSV, parse timestamps, normalize column types, cache in memory | Dev C |
| 1.3 | Sampler: deterministic sampling (keep all laundering-labeled rows + stratified sample of normal) | Dev C |
| 1.4 | SQLite audit store: table for flags & queries (id, query_id, reason, rule/version, timestamp) | Dev B |
| 1.5 | Base profiling & summary stats utilities (transaction counts, entity cardinalities, volume) | Dev A |
| 1.6 | Document dataset schema, sampling logic, and data contracts in README | Dev B |

**Milestone:** `load_data()` returns clean sampled DataFrame; Pydantic schemas and database models locked in.

---

## Phase 2 — The Tool & Detection Layer (Split, ~8h, core AML substance)

Each tool is a plain Python function with a clear input/output contract. Build and
unit-test each independently before the agent wires them together.

| # | Tool | What it does | Owner |
|---|------|--------------|-------|
| 2.1 | `eda.py` | Profiling, volume distributions, base-rate statistics, top counterparties | Dev A |
| 2.2 | `features.py` | Rolling sums, transaction velocity, sub-$10k counts, deviation, fan-out/fan-in degree | Dev C |
| 2.3 | `detectors.py` (Rules) | Deterministic rule detectors: structuring, smurfing, rapid layering, fan-out patterns | Dev B |
| 2.4 | `detectors.py` (ML) | Isolation Forest anomaly detector trained on engineered features → anomaly score | Dev C |
| 2.5 | `risk.py` | Hybrid risk fusion: combines rule flags + ML anomaly score → low/med/high + numeric score | Dev B |
| 2.6 | `explain.py` | Typology-tied natural-language reason generator per flag (with cited transaction IDs) | Dev A |

**Milestone:** Each tool runs standalone on sampled data with unit tests and returns structured output.

---

## Phase 3 — The Agent Orchestrator & API (Split, ~6h, the differentiator)

This is what makes it "agentic" — the LLM parses the query and builds a dynamic execution plan;
the deterministic tools execute the work.

| # | Task | What it does | Owner |
|---|------|--------------|-------|
| 3.1 | Intent Parser | LLM parses natural language query → `{intent, filters, entities, pattern, time_window}` | Dev A |
| 3.2 | Dynamic Planner | Intent → ordered list of tool calls (identifies tools to invoke and tools to skip with reasons) | Dev B |
| 3.3 | Plan Executor | Runs plan sequentially, passes data between tools, catches errors, aggregates results | Dev C |
| 3.4 | Result Synthesizer | LLM transforms raw tool outputs + execution plan into executive summary & key AML findings | Dev A |
| 3.5 | `ExecutionTrace` Logger | Records intent, active filters, invoked tools, skipped tools with rationale, and execution timings | Dev C |
| 3.6 | FastAPI Endpoints | `/query` endpoint (NL query in → plan + flags + trace out) and `/audit` flag feedback endpoint | Dev B |

**Milestone:** `POST /query` returns structured response containing the dynamic execution plan and deterministic flags.
**Determinism check:** Flag decisions originate from deterministic tools, not LLM hallucinations.

---

## Phase 4 — Frontend Dashboard & Visualizations (Split, ~6h)

| # | Component | What it displays / does | Owner |
|---|-----------|-------------------------|-------|
| 4.1 | Query Bar & Presets | Search input with quick-query pill buttons, submit action, loading skeletons | Dev B |
| 4.2 | **Execution Plan Panel** | Visual timeline/stepper showing detected intent, active filters, tools invoked vs skipped | Dev A |
| 4.3 | Results Table & Risk Badges | Paginated/sortable table of flagged transactions/accounts, risk badges (High/Med/Low) | Dev B |
| 4.4 | Explanation & Evidence Drawer | Expandable drawer showing typology classification, triggered rules, and cited transactions | Dev A |
| 4.5 | Analytics & Distribution Charts | Amount distribution histogram, risk tier breakdown donut, velocity trend charts | Dev C |
| 4.6 | Entity Drill-Down View | Account-level 360° view (transaction history, counterparties, risk history) for single lookups | Dev C |

**Milestone:** End-to-end interactive UI where entering a query renders the execution plan, results table, explanation, and visual analytics.

---

## Phase 5 — Demo Wiring, Evaluation & Polish (All 3, ~4h)

| # | Task | Owner |
|---|------|-------|
| 5.1 | Verify the 4 core demo queries produce **visibly distinct** tool execution paths | Dev A (Lead) + All |
| 5.2 | Precision / Recall / F1 validation script against IBM ground-truth labels (`validate.py`) | Dev C |
| 5.3 | Preset scenario buttons & mock query fallback for zero-latency live judging | Dev B |
| 5.4 | End-to-end testing, error handling fallbacks, response caching | Dev C |
| 5.5 | README finalization: setup instructions, architecture diagram, methodology, AI tool disclosure | Dev B |
| 5.6 | 2-slide pitch deck + 2-minute video demo recording & narration | All 3 (Dev A Lead) |

**Milestone:** Clean clone-and-run verification, passing test suite, final slide deck and demo video ready.

---

## Suggested Demo Script (The 2-Minute Video)

1. `"Analyse this dataset for suspicious activity"` → Full pipeline: EDA + Feature Eng + ML Anomaly + Rules + Charts.
2. `"Find structuring patterns in the last 30 days"` → Temporal filter, runs Structuring Detector, **skips EDA & ML** (Execution Plan panel highlights skipped steps).
3. `"Which customers made 10+ transactions under $10,000?"` → Pure aggregation & rule filtering, **no ML invoked** (Plan shows ML skipped).
4. `"Is customer 4521 suspicious?"` → Single-entity drill-down, on-demand risk scoring and counterparty visualization.

> **Key Demo Impact:** The **Execution Plan panel adapting dynamically** between queries demonstrates that the agent makes intelligent workflow decisions rather than executing a hardcoded pipeline.

---

## Collaboration & Git Strategy

- **Branching Model:** Create short-lived feature branches (`feat/eda-tool`, `feat/exec-plan-ui`, `feat/isolation-forest`) and merge via Pull Requests.
- **Commit Traceability:** Every team member must have visible commits across backend, agent/ML, and frontend to clearly showcase individual contributions.
- **Interface Stability:** Keep Pydantic schemas in `backend/app/models/` as the single source of truth across all tools and agent components.

