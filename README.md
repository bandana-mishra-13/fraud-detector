# Argus AML — Agentic Financial Crime Investigation & Compliance Platform

**Argus AML** is a production-grade, agentic Anti-Money Laundering (AML) investigation and explainability platform. It bridges natural language querying with deterministic rule detection, machine learning anomaly detection, dynamic agentic execution planning, and transparent compliance explainability to empower financial intelligence units, compliance officers, and regulatory auditors.

---

## 🏛️ System Architecture

```text
                                 ┌─────────────────────────────────┐
                                 │   Natural Language User Query   │
                                 └────────────────┬────────────────┘
                                                  │
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │      Agentic Intent Parser      │
                                 │  (Intent, Filters, Entities)    │
                                 └────────────────┬────────────────┘
                                                  │
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │     Dynamic Execution Plan      │
                                 │  (Invoked vs. Skipped Tools)    │
                                 └──────┬──────────────────┬───────┘
                                        │                  │
                    ┌───────────────────┘                  └──────────────────┐
                    ▼                                                         ▼
    ┌───────────────────────────────┐                         ┌───────────────────────────────┐
    │   Deterministic Rule Engine   │                         │  ML Isolation Forest Detector │
    │ (Structuring, Fan-Out, Layer) │                         │  (Engineered Feature Scoring) │
    └───────────────┬───────────────┘                         └───────────────┬───────────────┘
                    │                                                         │
                    └───────────────────┐                  ┌──────────────────┘
                                        ▼                  ▼
                                 ┌─────────────────────────────────┐
                                 │       Hybrid Risk Fusion        │
                                 │   (Risk Tier, Score 0.0-1.0)    │
                                 └────────────────┬────────────────┘
                                                  │
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │      Explainability Engine      │
                                 │ (Typology Reasons & Evidence)   │
                                 └──────┬──────────────────┬───────┘
                                        │                  │
                    ┌───────────────────┘                  └──────────────────┐
                    ▼                                                         ▼
    ┌───────────────────────────────┐                         ┌───────────────────────────────┐
    │      SQLite Audit Store       │                         │      Next.js Dashboard        │
    │  (Queries, Flags & Feedback)  │                         │ (Execution Plan, Table & Draw)│
    └───────────────────────────────┘                         └───────────────────────────────┘
```

---

## 🎯 4 Core Demo Investigation Scenarios

The platform dynamically schedules analytical tools according to query intent, ensuring optimal latency and compliance clarity:

| # | Demo Query | Detected Intent | Invoked Tools | Skipped Tools & Rationale |
|---|:---|:---|:---|:---|
| **1** | `"Analyse this dataset for suspicious activity"` | `BROAD_ANALYSIS` | `eda`, `features`, `detectors_ml`, `detectors_rules`, `risk`, `explain` | *None* — Full investigative pipeline for global baseline screening. |
| **2** | `"Find structuring patterns in the last 30 days"` | `PATTERN_DETECTION` | `detectors_rules`, `risk`, `explain` | **`eda`**, **`detectors_ml`**, **`features`** — Bypassed because structuring criteria and temporal filters are strictly deterministic. |
| **3** | `"Which customers made 10+ transactions under $10,000?"` | `AGGREGATION` | `features`, `detectors_rules`, `risk`, `explain` | **`detectors_ml`**, **`eda`** — Unsupervised ML is bypassed because exact threshold counting requires deterministic aggregation. |
| **4** | `"Is customer 4521 suspicious?"` | `ENTITY_INVESTIGATION` | `eda`, `features`, `detectors_rules`, `detectors_ml`, `risk`, `explain` | *Scoped to Entity 4521* — 360° entity drill-down combining counterparty profiling, flow analysis, and ML scoring. |

---

## 📊 Dataset Schema & Specifications

Argus AML is configured to ingest the standard **IBM Transactions for Anti-Money Laundering (AML)** dataset (`HI-Small_Trans.csv` with ~3.2M transactions) alongside a curated synthetic testing dataset (`synthetic_transactions.csv`).

### Column Data Dictionary

| Original Column Header | Canonical Schema Field | Data Type | Constraint / Domain | Description |
|:---|:---|:---|:---|:---|
| `Timestamp` | `timestamp` | `datetime` / `string` | ISO / `YYYY/MM/DD HH:MM` | Timestamp of the transaction occurrence |
| `From Bank` | `from_bank` | `string` | Bank ID / Name | Originating financial institution |
| `From Account` / `Account` | `from_account` | `string` | Non-empty string | Source account identifier sending funds |
| `To Bank` | `to_bank` | `string` | Bank ID / Name | Beneficiary financial institution |
| `To Account` / `Account.1` | `to_account` | `string` | Non-empty string | Destination account identifier receiving funds |
| `Amount Received` | `amount_received` | `float` | `ge=0.0` | Amount credited to destination account |
| `Receiving Currency` | `receiving_currency` | `string` | Currency ISO/Name | Currency format received (e.g., `US Dollar`) |
| `Amount Paid` | `amount_paid` | `float` | `ge=0.0` | Amount debited from origin account |
| `Payment Currency` | `payment_currency` | `string` | Currency ISO/Name | Currency format paid (e.g., `US Dollar`) |
| `Payment Format` | `payment_format` | `string` | `Wire`, `Cash`, `ACH`, etc. | Payment mechanism / transfer instrument |
| `Is Laundering` | `is_laundering` | `int` | `{0, 1}` | Ground-truth label (`1` = Suspicious / Laundering, `0` = Legitimate) |

---

## 🔬 Deterministic Stratified Sampling

Financial crime datasets exhibit extreme class imbalance (<0.1% positive laundering cases). To support rapid evaluation and responsive testing without losing positive signals, the sampler (`sampler.py`) implements a deterministic stratified strategy:

1. **100% Positive Signal Preservation**: Retains all rows where `Is Laundering == 1`, preserving all ground-truth money laundering typologies and graph structures.
2. **Reproducible Stratified Normal Sample**: Samples a configurable number $N$ of negative/legitimate transactions (`Is Laundering == 0`) using a fixed seed (`random_state=42`).
3. **Immutability Guarantee**: Original DataFrames are preserved without in-place mutation.

---

## 📐 Core Data Contracts & Pydantic Schemas

All analytical tools, agent components, and database models communicate through strictly validated Pydantic v2 schemas located in `app.models.schemas`:

- **`Transaction`**: Individual financial transaction with alias mapping.
- **`Flag`**: Suspicious finding with `rule_id`, `severity` (`RiskTier`: LOW, MEDIUM, HIGH, CRITICAL), `entity_id`, `transaction_ids`, `typology`, `reason`, and structured metric `evidence`.
- **`ExecutionPlan`**: Dynamic agent plan detailing `query`, `detected_intent`, `active_filters`, `target_entities`, `steps`, `invoked_tools`, and `skipped_tools` with explicit rationale.
- **`RiskResult`**: Fused entity or transaction risk assessment combining rule heuristics and ML scores $\in [0.0, 1.0]$.
- **`ExecutionTrace`**: End-to-end execution telemetry tracking `execution_timings_ms`, `total_execution_time_ms`, invoked/skipped tools, and workflow status.
- **`SynthesizedResult`**: Executive summary, bulleted key findings, cited transaction IDs, and investigative limitations.

---

## 🗄️ SQLite Audit Store & Compliance Traceability

The platform includes an embedded SQLite audit store (`AuditStore`) with Write-Ahead Logging (WAL) enabled for concurrency, resilience, and regulatory compliance.

### Storage Tables

1. **`audit_queries`**: Records every natural language search, parsed intent, filters applied, tools invoked vs. skipped, execution timings, and trace status.
2. **`audit_flags`**: Stores detected AML flags, rule versions, severity tiers, typology classifications, reason statements, and evidence metrics.
3. **`audit_feedback`**: Maintains an immutable chronological audit trail of compliance officer determinations (`CONFIRMED_SUSPICIOUS`, `FALSE_POSITIVE`, `UNDER_REVIEW`, `DISMISSED`) and investigative notes.

---

## 🌐 API Endpoints Reference

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Backend service health and latency check |
| `POST` | `/api/v1/query` | Natural language AML query in $\to$ dynamic plan, flags, risk score, trace & summary out |
| `POST` | `/api/v1/audit/feedback` | Record compliance analyst review determination on a flag |
| `GET` | `/api/v1/audit/queries` | List historical query audit logs with pagination and filters |
| `GET` | `/api/v1/audit/queries/{id}` | Get specific query audit record |
| `GET` | `/api/v1/audit/flags` | List detected AML flags with severity/status filters |
| `GET` | `/api/v1/audit/flags/{id}` | Get flag details and full chronological feedback history |
| `GET` | `/api/v1/audit/summary` | Aggregate audit statistics (query count, flag breakdown, feedback status) |

---

## 🚀 Quickstart & Setup

### Prerequisites
- Python 3.10+ (Recommended: Python 3.12)
- Node.js 18+ and npm

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run complete test suite (170 unit tests)
pytest -v

# Start FastAPI backend server
uvicorn app.main:app --reload --port 8000
```

Interactive documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

Web Dashboard: `http://localhost:3000`

---

## 📜 Citations, Disclosures & Ground Rules

- **Dataset Citation**: IBM Transactions for Anti-Money Laundering (AML) Synthetic Dataset (IEEE / Kaggle AML benchmark).
- **Tooling Stack**: FastAPI, Pydantic v2, Pandas, Scikit-Learn (Isolation Forest), SQLite (WAL), Next.js 14, Tailwind CSS, Lucide Icons.
- **AI Pair-Programming Disclosure**: Built using modern software development practices with AI pair-programming assistance.
- **Compliance Policy**: All institutional entities and financial institutions in this repository are generic, synthetic, or publicly benchmarked.
