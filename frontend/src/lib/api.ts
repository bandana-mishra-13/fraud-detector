import { getMockResponseForQuery } from "./mockData";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type RiskTier = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface HealthStatus {
  status: "ok" | "error" | "loading" | "unreachable";
  service?: string;
  version?: string;
  timestamp?: string;
  environment?: string;
  latencyMs?: number;
  error?: string;
}

export interface PlanStep {
  step_number: number;
  tool_name: string;
  description: string;
  parameters: Record<string, any>;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "SKIPPED" | "FAILED";
  result_summary?: string | null;
}

export interface SkippedTool {
  tool_name: string;
  reason: string;
}

export interface ExecutionPlan {
  plan_id: string;
  query: string;
  detected_intent: string;
  active_filters: Record<string, any>;
  target_entities: string[];
  steps: PlanStep[];
  invoked_tools: string[];
  skipped_tools: SkippedTool[];
  reasoning: string;
  created_at: string;
}

export interface Flag {
  flag_id: string;
  rule_id: string;
  rule_name: string;
  severity: RiskTier;
  entity_id?: string | null;
  transaction_ids: string[];
  typology?: string | null;
  reason: string;
  evidence: Record<string, any>;
  feedback_status?: string;
  analyst_notes?: string | null;
  timestamp: string;
}

export interface RiskResult {
  result_id: string;
  entity_id?: string | null;
  transaction_id?: string | null;
  risk_score: number;
  risk_tier: RiskTier;
  flags: Flag[];
  rule_score?: number | null;
  ml_score?: number | null;
  summary: string;
  evidence_summary: Record<string, any>;
  created_at: string;
}

export interface SynthesizedResult {
  executive_summary: string;
  key_findings: string[];
  cited_transaction_ids: string[];
  limitations: string[];
}

export interface ExecutionTrace {
  trace_id: string;
  query_id?: string | null;
  detected_intent: string;
  active_filters: Record<string, any>;
  invoked_tools: string[];
  skipped_tools: SkippedTool[];
  execution_timings_ms: Record<string, number>;
  total_execution_time_ms: number;
  status: "SUCCESS" | "FAILED" | "PARTIAL_SUCCESS";
  error_message?: string | null;
  created_at: string;
}

export interface ParsedIntent {
  query: string;
  intent: string;
  filters: Record<string, any>;
  entities: string[];
  pattern?: string | null;
  time_window?: any;
}

export interface QueryResponse {
  query_id: string;
  query: string;
  parsed_intent: ParsedIntent;
  execution_plan: ExecutionPlan;
  flags: Flag[];
  risk_result?: RiskResult | null;
  synthesized_result?: SynthesizedResult | null;
  trace: ExecutionTrace;
  explanations: Array<Record<string, any>>;
  eda_summary?: Record<string, any> | null;
}

export interface AuditSummary {
  total_queries: number;
  total_flags: number;
  total_feedback_events: number;
  flags_by_severity: Record<string, number>;
  flags_by_feedback_status: Record<string, number>;
  top_triggered_rules: Array<{ rule_id: string; rule_name: string; count: number }>;
}

export interface FeedbackResponse {
  feedback_id: string;
  flag_id: string;
  query_id?: string | null;
  feedback_status: string;
  analyst_id: string;
  notes: string;
  reviewed_at: string;
}

/**
 * Checks health of the Argus AML FastAPI backend
 */
export async function checkBackendHealth(): Promise<HealthStatus> {
  const startTime = performance.now();
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const latencyMs = Math.round(performance.now() - startTime);

    if (!res.ok) {
      return {
        status: "error",
        latencyMs,
        error: `HTTP ${res.status}: ${res.statusText}`,
      };
    }

    const data = await res.json();
    return {
      status: "ok",
      service: data.service,
      version: data.version,
      timestamp: data.timestamp,
      environment: data.environment,
      latencyMs,
    };
  } catch (err: unknown) {
    const latencyMs = Math.round(performance.now() - startTime);
    const errorMessage =
      err instanceof Error ? err.message : "Failed to connect to backend service";
    return {
      status: "unreachable",
      latencyMs,
      error: errorMessage,
    };
  }
}

/**
 * Executes an AML natural language investigation query with automatic fallback.
 */
export async function sendInvestigationQuery(
  query: string,
  options?: {
    forceMock?: boolean;
    datasetPath?: string;
    normalSampleSize?: number;
  }
): Promise<{ data: QueryResponse; isMock: boolean; latencyMs: number }> {
  const startTime = performance.now();

  // If forced mock mode is on
  if (options?.forceMock) {
    await new Promise((resolve) => setTimeout(resolve, 350));
    return {
      data: getMockResponseForQuery(query),
      isMock: true,
      latencyMs: Math.round(performance.now() - startTime),
    };
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        query: query.trim(),
        dataset_path: options?.datasetPath,
        normal_sample_size: options?.normalSampleSize,
      }),
      cache: "no-store",
    });

    const latencyMs = Math.round(performance.now() - startTime);

    if (!res.ok) {
      console.warn(`Backend responded with ${res.status}. Falling back to zero-latency mock.`);
      return {
        data: getMockResponseForQuery(query),
        isMock: true,
        latencyMs,
      };
    }

    const data = await res.json();
    return {
      data,
      isMock: false,
      latencyMs,
    };
  } catch (err) {
    console.warn("API request failed. Falling back to zero-latency mock response:", err);
    return {
      data: getMockResponseForQuery(query),
      isMock: true,
      latencyMs: Math.round(performance.now() - startTime),
    };
  }
}

/**
 * Submits compliance officer feedback for an AML flag.
 */
export async function submitAnalystFeedback(params: {
  flagId: string;
  feedbackStatus: string;
  analystId?: string;
  notes?: string;
  queryId?: string;
}): Promise<FeedbackResponse> {
  const payload = {
    flag_id: params.flagId,
    feedback_status: params.feedbackStatus,
    analyst_id: params.analystId || "compliance_analyst",
    notes: params.notes || "",
    query_id: params.queryId || null,
  };

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/audit/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }

    return await res.json();
  } catch (err) {
    // Local optimistic mock update
    return {
      feedback_id: `fb-local-${Date.now()}`,
      flag_id: params.flagId,
      query_id: params.queryId,
      feedback_status: params.feedbackStatus,
      analyst_id: params.analystId || "compliance_analyst",
      notes: params.notes || "",
      reviewed_at: new Date().toISOString(),
    };
  }
}

/**
 * Fetches compliance audit summary metrics.
 */
export async function fetchAuditSummary(): Promise<AuditSummary | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/audit/summary`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
