/** Mirrors the backend's RiskResult response (app/models/schemas.py). */

export type RiskLevel = "low" | "medium" | "high";
export type EscalationAction = "monitor" | "review" | "report";
export type StepAction = "invoked" | "skipped";

export interface PlanStep {
    tool: string;
    action: StepAction;
    reason: string;
    params: Record<string, unknown>;
    duration_ms: number | null;
}

export interface ExecutionPlan {
    query: string;
    intent: string;
    pattern: string | null;
    filters: Record<string, unknown>;
    steps: PlanStep[];
}

export interface Flag {
    entity_type: "transaction" | "account" | "customer";
    entity_id: string;
    pattern: string;
    risk_level: RiskLevel;
    score: number;
    reason: string;
    escalation: EscalationAction;
    evidence: Record<string, unknown>;
}

export interface AggregationRow {
    account: string;
    customer: string;
    txn_count: number;
    total: number;
}

export interface PriorFlag {
    entity_id: string;
    pattern: string;
    risk_level: string;
    reason: string;
    flagged_at: string;
}

export interface Kpis {
    transactions_scanned: number;
    flags_raised: number;
    high_risk: number;
    elapsed_ms: number;
    flags_shown?: number;
    aggregation_matches?: number;
    aggregation_shown?: number;
    eda_summary?: Record<string, unknown>;
}

export interface Charts {
    txns_per_day?: { date: string; count: number; volume: number }[];
    payment_formats?: { format: string; count: number }[];
    currencies?: { currency: string; count: number }[];
    top_senders?: { account: string; count: number; volume: number }[];
    amount_hist?: { bin_low: number; bin_high: number; count: number }[];
    risk_breakdown?: { level: string; count: number }[];
    aggregation_table?: AggregationRow[];
    prior_flags?: PriorFlag[];
    entity_accounts?: string[];
}

export interface RiskResult {
    run_id: string;
    plan: ExecutionPlan;
    flags: Flag[];
    kpis: Kpis;
    charts: Charts;
    summary: string;
    llm_warning?: string;
}

/** One query + its result, belonging to a session. */
export interface SessionRun {
    id: string;
    query: string;
    startedAt: number;
    result: RiskResult;
}

/** A working session — a named group of runs. */
export interface Session {
    id: string;
    name: string;
    createdAt: number;
    runs: SessionRun[];
}
