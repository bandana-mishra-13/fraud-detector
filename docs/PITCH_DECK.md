# Argus AML — 2-Slide Pitch Deck

---

## SLIDE 1: Problem & Agentic Solution

### 🚩 The Problem: Legacy Rule Explosion & LLM Hallucinations
* **False Positive Fatigue:** Financial institutions process millions of daily transactions using static, rigid rules that yield **90%+ false-positive rates**, costing compliance teams billions in manual review overhead.
* **LLM Financial Risks:** GenAI solutions often **hallucinate fraud decisions, invent non-existent transaction IDs, or alter risk scores**, violating strict AML regulatory auditing standards.
* **Lack of Adaptability:** Fixed pipelines run heavy machine learning and exploratory models on simple queries, creating latency bottlenecks and unnecessary compute expense.

### 🛡️ The Solution: Argus Agentic AML Platform
* **Deterministic Core, LLM Presentation Layer:** AI intent parsing and execution planning orchestrate **100% deterministic Python tools** (Isolation Forest ML, Structuring Rules, Risk Fusion, Typology Explainability).
* **Zero Hallucination Guarantee:** The LLM NEVER generates flags or risk scores. All risk tiers, numeric scores, and transaction IDs originate from verified algorithmic tools.
* **Dynamic Execution Planning:** Automatically adapts the analytical workflow per query—invoking deep ML for broad scans, while **dynamically bypassing redundant tools** for targeted typology searches.

---

## SLIDE 2: Agentic Architecture & Live Demo Impact

### ⚙️ System Architecture (Vertical Slice Architecture)
```text
Natural Language Query
        │
        ▼
[Dev A] Intent Parser (LLM) ──► ParsedIntent (Schema)
        │
        ▼
[Dev B] Dynamic Planner (LLM/Rule) ──► ExecutionPlan (Invoked vs. Skipped Tools)
        │
        ▼
[Dev C] Plan Executor ──► Standalone Tools:
        ├── 1. EDA Profiling (Dev A)
        ├── 2. Rolling Feature Eng. (Dev C)
        ├── 3. Isolation Forest ML Anomaly Detection (Dev C)
        ├── 4. Deterministic Rule Detectors (Dev B)
        ├── 5. Hybrid Risk Fusion Engine (Dev B)
        └── 6. Typology-Tied Explainability (Dev A)
        │
        ▼
[Dev A] Result Synthesizer & Explanation Drawer ──► Executive Summary + Cited Evidence
```

### 🎬 The 4 Core Demo Scenarios (Visible Execution Path Adaptation)
1. **Query 1:** `"Analyse this dataset for suspicious activity"`  
   * **Pipeline Path:** Full 6-Tool Pipeline (EDA → Features → ML → Rules → Risk → Explain).
2. **Query 2:** `"Find structuring patterns in the last 30 days"`  
   * **Pipeline Path:** Targeted Temporal Rule Engine. **Bypasses EDA & ML** to eliminate latency & noise.
3. **Query 3:** `"Which customers made 10+ transactions under $10,000?"`  
   * **Pipeline Path:** Aggregation & Threshold Filter. **Bypasses ML Anomaly scoring**.
4. **Query 4:** `"Is customer 4521 suspicious?"`  
   * **Pipeline Path:** 360° Entity Drill-down & Counterparty Risk Profiling.

### 🚀 Key Impact & Tech Stack
* **Tech Stack:** FastAPI (Python 3.12), Pydantic v2, Scikit-Learn (Isolation Forest), SQLite Audit Store, Next.js 14, Tailwind CSS, OpenRouter API.
* **Compliance Auditability:** Full telemetry logging (`ExecutionTrace`) records exact plan execution times, invoked tools, and analyst feedback audit trail.
