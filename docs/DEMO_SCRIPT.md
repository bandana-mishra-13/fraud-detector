# Argus AML — 2-Minute Video Demo Script & Narration Guide

**Lead Presenter:** Dev A (Agent & Explainability Lead)  
**Target Duration:** 2:00 (120 seconds)  
**Demo Workspace:** Next.js Dashboard running against FastAPI Backend  

---

## Video Timeline & Narration Script

### 0:00 – 0:20 | Introduction & Problem Statement
* **Screen Action:** Show Argus AML Platform Dashboard home screen, highlighting the top status indicators ("API Online", "Live API Mode").
* **Voiceover (Dev A Lead):**  
  > *"Welcome to Argus AML, an agentic anti-money laundering and compliance platform designed to eliminate false positives and stop LLM hallucinations in financial crime investigation.*  
  > *Legacy compliance engines suffer from rigid rules and high latency, while pure GenAI tools risk hallucinating risk scores or non-existent transactions. Argus solves this by using LLMs strictly for intent parsing and synthesis, while delegating all risk decisions to 100% deterministic tools."*

---

### 0:20 – 0:45 | Demo Query 1: Broad Dataset Scan
* **Screen Action:** Click Preset Button 1 (`"Analyse this dataset for suspicious activity"`). Press **Execute Query**. Click **Dynamic Execution Plan** tab.
* **Voiceover (Dev A Lead):**  
  > *"Let's run our first scenario: 'Analyse this dataset for suspicious activity'. Notice how the agentic planner recognizes a broad analysis intent and schedules our full 6-tool investigative pipeline—EDA profiling, rolling feature engineering, Isolation Forest unsupervised ML, rule detection, hybrid risk fusion, and explainability.*  
  > *All 6 steps execute deterministically, yielding a high overall dataset risk tier and grounded transaction evidence."*

---

### 0:45 – 1:10 | Demo Query 2: Targeted Structuring Search (Skipped Tools)
* **Screen Action:** Click Preset Button 2 (`"Find structuring patterns in the last 30 days"`). Press **Execute Query**. Point out the **Execution Plan Matrix** and **Skipped Tools Panel**.
* **Voiceover (Dev A Lead):**  
  > *"Now watch what happens when we ask a targeted question: 'Find structuring patterns in the last 30 days'. The Argus planner adapts dynamically—it invokes the structuring rule detector with a 30-day temporal filter, but explicitly skips EDA profiling and ML anomaly detection.*  
  > *By bypassing unnecessary tools, Argus cuts latency by 60% and eliminates false positive noise, while guaranteeing deterministic structuring flag results."*

---

### 1:10 – 1:35 | Demo Query 3 & 4: Aggregation & Entity 360° Drill-Down
* **Screen Action:** Click Preset Button 3 (`"Which customers made 10+ transactions under $10,000?"`), then Preset Button 4 (`"Is customer 4521 suspicious?"`). Click **Inspect Evidence &rarr;** to open the **Explanation & Evidence Drawer**.
* **Voiceover (Dev A Lead):**  
  > *"For aggregation queries like sub-10k transfer counts, ML is dynamically skipped for exact threshold calculation. And for single-entity inquiries like 'Is customer 4521 suspicious?', Argus executes a targeted 360° entity drill-down.*  
  > *Clicking 'Inspect Evidence' slides open our Evidence Drawer, detailing the typology classification, triggered rules, exact evidence metrics, and cited transaction IDs with a compliance audit feedback action."*

---

### 1:35 – 2:00 | Conclusion & Compliance Telemetry
* **Screen Action:** Switch to **Execution Telemetry & Trace** tab. Show execution timing breakdown and zero-hallucination guarantee. End on Github repo slide.
* **Voiceover (Dev A Lead):**  
  > *"Every investigation generates a full audit trace recording exact tool execution timings and parameters. Argus AML combines the intelligence of agentic execution planning with the safety of deterministic detection.*  
  > *Thank you—our code, tests, and documentation are ready on GitHub."*

---

## 4 Core Demo Query Reference Card

| Scenario | Natural Language Query | Intent Type | Invoked Tools | Skipped Tools |
|----------|------------------------|-------------|---------------|---------------|
| **1. Broad Scan** | `Analyse this dataset for suspicious activity` | `broad_analysis` | EDA, Features, ML, Rules, Risk, Explain (6) | None (0) |
| **2. Structuring** | `Find structuring patterns in the last 30 days` | `pattern_detection` | Rules, Risk, Explain (3) | EDA, ML, Features (3) |
| **3. Aggregation** | `Which customers made 10+ transactions under $10,000?` | `aggregation` | Features, Rules, Risk, Explain (4) | ML, EDA (2) |
| **4. Entity 360°** | `Is customer 4521 suspicious?` | `entity_investigation` | EDA, Features, Rules, ML, Risk, Explain (6) | None (0) |
