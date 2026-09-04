# Argus AML — Agentic Financial Crime Investigation & Explainability Platform

**Argus AML** is an advanced Anti-Money Laundering (AML) investigation and compliance platform. It bridges natural language querying with deterministic rule engines, machine learning anomaly detection, dynamic agentic execution planning, and transparent explainability to empower financial intelligence units and compliance analysts.

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

## 📊 Dataset Schema & Specifications

Argus AML is configured to ingest the standard **IBM Transactions for Anti-Money Laundering (AML)** dataset (`HI-Small_Trans.csv` with ~3.2M transactions) alongside a curated synthetic testing dataset (`synthetic_transactions.csv`).

### Column Data Dictionary

| Original Column Header | Canonical Schema Field | Data Type | Constraint / Domain | Description |
|:---|:---|:---|:---|:---|
| `Timestamp` | `timestamp` | `datetime` / `string` | ISO / `YYYY/MM/DD HH:MM` | Timestamp of the transaction occurrence |
| `From Bank` | `from_bank` | `string` | Bank ID / Name | Identifier of the originating financial institution |
| `From Account` / `Account` | `from_account` | `string` | Non-empty string | Source account identifier sending funds |
| `To Bank` | `to_bank` | `string` | Bank ID / Name | Identifier of the beneficiary financial institution |
| `To Account` / `Account.1` | `to_account` | `string` | Non-empty string | Destination account identifier receiving funds |
| `Amount Received` | `amount_received` | `float` | `ge=0.0` | Amount credited to the destination account |
| `Receiving Currency` | `receiving_currency` | `string` | Currency ISO/Name | Currency format received (e.g., `US Dollar`) |
| `Amount Paid` | `amount_paid` | `float` | `ge=0.0` | Amount debited from the origin account |
| `Payment Currency` | `payment_currency` | `string` | Currency ISO/Name | Currency format paid (e.g., `US Dollar`) |
| `Payment Format` | `payment_format` | `string` | `Wire`, `Cash`, `ACH`, etc. | Payment mechanism / transfer instrument |
| `Is Laundering` | `is_laundering` | `int` | `{0, 1}` | Ground-truth AML label (`1` = Suspicious / Laundering, `0` = Legitimate) |

### Header Normalization
The data loader (`data_loader.py`) automatically maps legacy IBM CSV headers (such as `Account` and `Account.1` / `Account_1`) to canonical names (`From Account` and `To Account`), ensuring backward and forward compatibility.

---

## 🔬 Deterministic Stratified Sampling

Financial crime datasets exhibit extreme class imbalance (typically <0.1% positive laundering cases). To support low-latency evaluation and testing without losing suspicious behavior patterns, the sampler (`sampler.py`) implements a deterministic stratified strategy:

1. **100% Positive Signal Preservation**: Extracts all rows where `Is Laundering == 1`, preserving all ground-truth money laundering typologies and graph structures.
2. **Reproducible Stratified Normal Sample**: Samples a configurable number $N$ of negative/legitimate transactions (`Is Laundering == 0`) using a fixed seed (`random_state=42`).
3. **Immutability Guarantee**: Input DataFrames are preserved without mutation, producing a fresh concatenated DataFrame with preserved dtypes and aligned index.

```python
from app.tools.data_loader import load_transactions
from app.tools.sampler import sample_transactions

# Load normalized dataset
df = load_transactions("synthetic_transactions.csv")

# Deterministic sample preserving all laundering signals + 500 normal rows
sampled_df = sample_transactions(df, normal_sample_size=500, random_state=42)
```

---

## 📐 Core Data Contracts & Pydantic Schemas

All analytical tools, agent components, and database models communicate through strictly validated Pydantic v2 schemas located in `app.models.schemas`:

### 1. `Transaction`
Represents an individual financial transaction event with alias-based serialization support for CSV ingestion and API payloads.

### 2. `Flag`
Structured finding generated by deterministic rule detectors or ML anomaly algorithms.
- `flag_id`: Unique UUID identifier.
- `rule_id`: Detector identifier (e.g., `STRUCTURING_01`, `RAPID_MOVEMENT_01`, `FAN_OUT_01`).
- `rule_name`: Human-readable detector title.
- `severity`: Risk tier (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- `entity_id`: Target account or bank identifier.
- `transaction_ids`: List of supporting transaction IDs.
- `typology`: Typology categorization (`Structuring`, `Pass-through`, `Fan-out`, `Smurfing`).
- `reason`: Detailed natural language explanation of the detection finding.
- `evidence`: Structured dictionary containing numerical metrics, threshold breaches, and timestamps.

### 3. `ExecutionPlan`
Dynamic execution plan synthesized by the agent orchestrator for an analyst query.
- `plan_id`: Unique plan UUID.
- `query`: Raw user natural language prompt.
- `detected_intent`: Inferred objective (e.g., `INVESTIGATE_ACCOUNT`, `TYPOLOGY_SEARCH`, `GLOBAL_SCAN`).
- `active_filters`: Inferred constraints (e.g., `time_window`, `min_amount`, `currency`).
- `target_entities`: Extracted entities/accounts.
- `steps`: Ordered list of tool execution steps (`PlanStep`).
- `invoked_tools`: Tool names scheduled for execution.
- `skipped_tools`: List of tools skipped along with an explicit compliance explanation (`SkippedTool`).

### 4. `RiskResult`
Fused entity or transaction risk assessment combining rule heuristics and ML scores.
- `risk_score`: Normalized continuous score $\in [0.0, 1.0]$.
- `risk_tier`: Discrete categorical tier (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- `rule_score`: Heuristic rule component score $\in [0.0, 1.0]$.
- `ml_score`: Isolation Forest anomaly component score $\in [0.0, 1.0]$.
- `flags`: List of contributing `Flag` objects.
- `summary`: High-level natural language executive summary.

### 5. `ExecutionTrace`
End-to-end execution telemetry for auditability and compliance verification.
- `trace_id`: Unique trace UUID.
- `execution_timings_ms`: Per-tool execution duration breakdown in milliseconds.
- `total_execution_time_ms`: Total end-to-end pipeline execution time.
- `status`: Overall workflow outcome (`SUCCESS`, `FAILED`, `PARTIAL_SUCCESS`).

---

## 🗄️ SQLite Audit Store & Compliance Traceability

The platform includes an embedded SQLite audit store (`AuditStore`) with Write-Ahead Logging (WAL) enabled for concurrency, resilience, and regulatory compliance.

### Storage Tables

1. **`audit_queries`**: Records every natural language search, parsed intent, filters applied, tools invoked vs. skipped, execution timings, and trace status.
2. **`audit_flags`**: Stores detected AML flags, rule versions, severity tiers, typology classifications, reason statements, and evidence metrics.
3. **`audit_feedback`**: Maintains an immutable chronological audit trail of compliance officer reviews (`CONFIRMED_SUSPICIOUS`, `FALSE_POSITIVE`, `UNDER_REVIEW`, `DISMISSED`) and investigative notes.

```python
from app.storage import get_audit_store

audit_store = get_audit_store()

# Log an investigation query
query_id = audit_store.log_query(
    query_text="Find structuring transactions above $9,000",
    detected_intent="TYPOLOGY_SEARCH",
    invoked_tools=["structuring_detector"],
    skipped_tools=[{"tool_name": "ml_anomaly", "reason": "Targeted rule search"}]
)

# Record analyst review feedback
audit_store.log_feedback(
    flag_id="flag-uuid-1234",
    feedback_status="CONFIRMED_SUSPICIOUS",
    analyst_id="analyst_smith",
    notes="Confirmed repeated sub-$10k deposits matching smurfing pattern."
)
```

---

## 🚀 Quickstart & Setup

### Prerequisites
- Python 3.10+ (Recommended: Python 3.12)
- Node.js 18+ and npm

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run test suite
pytest -v

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

The API documentation is accessible at:
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

The web dashboard is accessible at `http://localhost:3000`.

---

## 📜 Citations, Disclosures & Ground Rules

- **Dataset Citation**: IBM Transactions for Anti-Money Laundering (AML) Synthetic Dataset (IEEE / Kaggle AML benchmark).
- **AI & Tooling Disclosure**: Developed using FastAPI, Pydantic v2, Pandas, Scikit-Learn, Next.js, Tailwind CSS, and AI pair-programming assistance.
- **Compliance Policy**: All institutional entities and financial institutions in this repository are generic, synthetic, or publicly benchmarked.
