"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  ShieldAlert,
  Activity,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Server,
  Layers,
  BrainCircuit,
  Search,
  Zap,
  BarChart3,
  ExternalLink,
  SlidersHorizontal,
  FileCode,
  Clock,
  Terminal,
  Database,
  Radio,
} from "lucide-react";
import {
  checkBackendHealth,
  HealthStatus,
  API_BASE_URL,
  QueryResponse,
  sendInvestigationQuery,
  Flag,
} from "@/lib/api";
import { QueryBar } from "@/components/QueryBar";
import { ResultsTable } from "@/components/ResultsTable";
import { ExecutionPlanTimeline } from "@/components/ExecutionPlanTimeline";
import { ExecutiveSummaryCard } from "@/components/ExecutiveSummaryCard";
import { ExplanationEvidenceDrawer, ExplanationDrawerData } from "@/components/ExplanationEvidenceDrawer";
import { AnalyticsCharts } from "@/components/AnalyticsCharts";
import { EntityDrillDown } from "@/components/EntityDrillDown";
import { getMockResponseForQuery } from "@/lib/mockData";

export default function Home() {
  const [health, setHealth] = useState<HealthStatus>({ status: "loading" });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [queryInput, setQueryInput] = useState("Find structuring patterns in the last 30 days");
  const [isLoading, setIsLoading] = useState(false);
  const [isMockMode, setIsMockMode] = useState(false);
  const [normalSampleSize, setNormalSampleSize] = useState(200);
  const [activeTab, setActiveTab] = useState<"summary" | "plan" | "results" | "trace" | "architecture">("summary");
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
  const [lastExecutionMeta, setLastExecutionMeta] = useState<{ isMock: boolean; latencyMs: number } | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerData, setDrawerData] = useState<ExplanationDrawerData | null>(null);

  const openDrawerForFlag = (flag: Flag) => {
    setDrawerData({
      flagId: flag.flag_id,
      ruleId: flag.rule_id,
      ruleName: flag.rule_name,
      typology: flag.typology || flag.rule_name,
      severity: flag.severity,
      entityId: flag.entity_id,
      summary: flag.reason,
      explanation: flag.reason,
      transactionIds: flag.transaction_ids,
      evidence: flag.evidence,
      timestamp: flag.timestamp,
    });
    setDrawerOpen(true);
  };

  const openDrawerForExplanation = (exp: Record<string, any>) => {
    setDrawerData({
      flagId: exp.flag_id || `EXP-${Math.random().toString(36).slice(2, 7)}`,
      ruleId: exp.rule_id || "RULE-DETECTOR",
      ruleName: exp.rule_name || "AML Typology Rule",
      typology: exp.typology || "AML Finding",
      severity: exp.severity || "HIGH",
      entityId: exp.entity_id,
      summary: exp.summary,
      explanation: exp.explanation || exp.summary,
      transactionIds: exp.transaction_ids || [],
      evidence: exp.evidence || {},
      timestamp: exp.timestamp,
    });
    setDrawerOpen(true);
  };

  const runHealthCheck = useCallback(async () => {
    setIsRefreshing(true);
    const result = await checkBackendHealth();
    setHealth(result);
    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    runHealthCheck();
    const interval = setInterval(runHealthCheck, 15000);
    return () => clearInterval(interval);
  }, [runHealthCheck]);

  // Load initial demo query on mount for instant visual presentation
  useEffect(() => {
    const initialResponse = getMockResponseForQuery("Find structuring patterns in the last 30 days");
    setQueryResponse(initialResponse);
    setLastExecutionMeta({ isMock: true, latencyMs: 25 });
  }, []);

  const handleExecuteQuery = async (queryText: string) => {
    setIsLoading(true);
    try {
      const result = await sendInvestigationQuery(queryText, {
        forceMock: isMockMode,
        normalSampleSize,
      });
      setQueryResponse(result.data);
      setLastExecutionMeta({ isMock: result.isMock, latencyMs: result.latencyMs });
    } catch (err) {
      console.error("Query execution error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#090d16]/85 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-sky-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-sky-500/25">
              <ShieldAlert className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold tracking-tight text-lg text-white">ARGUS</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/30 font-mono font-semibold">
                  AML Platform
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">Agentic Anti-Money Laundering & Compliance Intelligence</p>
            </div>
          </div>

          {/* Backend Health & Mode Indicators */}
          <div className="flex items-center space-x-3">
            {lastExecutionMeta && (
              <div
                className={`hidden md:inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono border ${
                  lastExecutionMeta.isMock
                    ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                    : "bg-sky-500/10 text-sky-300 border-sky-500/30"
                }`}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-current"></span>
                <span>{lastExecutionMeta.isMock ? "Mock Fallback" : "Live API"}</span>
                <span className="opacity-60">({lastExecutionMeta.latencyMs}ms)</span>
              </div>
            )}

            <div
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                health.status === "ok"
                  ? "bg-emerald-950/40 text-emerald-400 border-emerald-500/30"
                  : health.status === "loading"
                  ? "bg-slate-800/60 text-slate-400 border-slate-700"
                  : "bg-rose-950/40 text-rose-400 border-rose-500/30"
              }`}
            >
              <span className="relative flex h-2 w-2">
                {health.status === "ok" && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                )}
                <span
                  className={`relative inline-flex rounded-full h-2 w-2 ${
                    health.status === "ok"
                      ? "bg-emerald-500"
                      : health.status === "loading"
                      ? "bg-slate-400"
                      : "bg-rose-500"
                  }`}
                ></span>
              </span>
              <span>
                {health.status === "ok"
                  ? `API Online (${health.latencyMs}ms)`
                  : health.status === "loading"
                  ? "Connecting..."
                  : "API Offline"}
              </span>
            </div>

            <button
              onClick={runHealthCheck}
              disabled={isRefreshing}
              title="Refresh backend status"
              className="p-1.5 rounded-lg border border-white/10 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            </button>

            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border border-white/10 hover:bg-slate-800 text-xs text-slate-300 transition-colors"
            >
              <span>Swagger Docs</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Section 1: Query Bar & Demo Presets (Task 4.1 & 5.3) */}
        <section className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                AML Agentic Investigation Hub
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
                Dynamic execution planning with deterministic rule detectors, Isolation Forest ML anomaly scoring, and typology-tied evidence explainability.
              </p>
            </div>
          </div>

          <QueryBar
            query={queryInput}
            setQuery={setQueryInput}
            onExecute={handleExecuteQuery}
            isLoading={isLoading}
            isMockMode={isMockMode}
            setIsMockMode={setIsMockMode}
            normalSampleSize={normalSampleSize}
            setNormalSampleSize={setNormalSampleSize}
          />
        </section>

        {/* Section 2: Results Display Workspace */}
        {queryResponse && (
          <section className="space-y-6">
            {/* Executive Summary Card (Task 3.4 / 4.4) */}
            <ExecutiveSummaryCard
              synthesizedResult={queryResponse.synthesized_result}
              riskResult={queryResponse.risk_result}
            />

            {/* Visual Analytics (Task 4.5) */}
            <AnalyticsCharts
              edaSummary={queryResponse.eda_summary}
              flags={queryResponse.flags}
            />

            {/* Entity Drill-Down (Task 4.6) */}
            <EntityDrillDown
              riskResult={queryResponse.risk_result}
              flags={queryResponse.flags}
              executionPlan={queryResponse.execution_plan}
              parsedIntent={queryResponse.parsed_intent}
              synthesizedResult={queryResponse.synthesized_result}
              edaSummary={queryResponse.eda_summary}
              onSelectFlag={openDrawerForFlag}
            />

            {/* Tab Navigation */}
            <div className="glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-xl">
              <div className="flex flex-wrap border-b border-white/10 px-4 pt-3 gap-2 sm:gap-6 text-xs sm:text-sm font-medium">
                <button
                  onClick={() => setActiveTab("summary")}
                  className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                    activeTab === "summary"
                      ? "border-sky-500 text-sky-400 font-semibold"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Activity className="h-4 w-4" />
                  <span>Overview & Metrics</span>
                </button>

                <button
                  onClick={() => setActiveTab("plan")}
                  className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                    activeTab === "plan"
                      ? "border-purple-500 text-purple-400 font-semibold"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <BrainCircuit className="h-4 w-4" />
                  <span>Dynamic Execution Plan ({queryResponse.execution_plan.steps.length} Steps)</span>
                </button>

                <button
                  onClick={() => setActiveTab("results")}
                  className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                    activeTab === "results"
                      ? "border-rose-500 text-rose-400 font-semibold"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <ShieldAlert className="h-4 w-4" />
                  <span>Flagged Detections & Actions ({queryResponse.flags.length})</span>
                </button>

                <button
                  onClick={() => setActiveTab("trace")}
                  className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                    activeTab === "trace"
                      ? "border-emerald-500 text-emerald-400 font-semibold"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Terminal className="h-4 w-4" />
                  <span>Execution Telemetry & Trace</span>
                </button>

                <button
                  onClick={() => setActiveTab("architecture")}
                  className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                    activeTab === "architecture"
                      ? "border-indigo-500 text-indigo-400 font-semibold"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Layers className="h-4 w-4" />
                  <span>Team Slices</span>
                </button>
              </div>

              <div className="p-6">
                {/* Tab 1: Overview */}
                {activeTab === "summary" && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* Risk Tier Metric Card */}
                      <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/5 space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span>Risk Categorization</span>
                          <span className="font-mono text-sky-400">{queryResponse.risk_result?.risk_score.toFixed(4) || "0.0000"}</span>
                        </div>
                        <div className="text-2xl font-black text-white">
                          {queryResponse.risk_result?.risk_tier || "LOW"}
                        </div>
                        <p className="text-[11px] text-slate-400">
                          Deterministic heuristic: {queryResponse.risk_result?.rule_score?.toFixed(2) || "0.00"} | ML anomaly score: {queryResponse.risk_result?.ml_score?.toFixed(2) || "N/A"}
                        </p>
                      </div>

                      {/* Total Flags Card */}
                      <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/5 space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span>Deterministic Red Flags</span>
                          <ShieldAlert className="h-4 w-4 text-rose-400" />
                        </div>
                        <div className="text-2xl font-black text-rose-400">
                          {queryResponse.flags.length} Findings
                        </div>
                        <p className="text-[11px] text-slate-400">
                          {Array.from(new Set(queryResponse.flags.map((f) => f.typology).filter(Boolean))).join(", ") || "No typology flags"}
                        </p>
                      </div>

                      {/* Execution Timing Card */}
                      <div className="p-5 rounded-2xl bg-slate-900/60 border border-white/5 space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span>Pipeline Latency</span>
                          <Clock className="h-4 w-4 text-emerald-400" />
                        </div>
                        <div className="text-2xl font-black text-emerald-400 font-mono">
                          {queryResponse.trace.total_execution_time_ms} ms
                        </div>
                        <p className="text-[11px] text-slate-400">
                          Status: <span className="font-semibold text-white">{queryResponse.trace.status}</span> &bull; {queryResponse.execution_plan.invoked_tools.length} Tools Invoked
                        </p>
                      </div>
                    </div>

                    {/* Explanations List */}
                    {queryResponse.explanations && queryResponse.explanations.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                          Typology Explainability Breakdowns (Dev A Task 2.6 / 4.4)
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {queryResponse.explanations.map((exp, idx) => (
                            <div
                              key={idx}
                              onClick={() => openDrawerForExplanation(exp)}
                              className="p-4 rounded-xl bg-slate-900/40 hover:bg-slate-900/90 border border-white/5 hover:border-sky-500/40 cursor-pointer transition-all space-y-2 text-xs group"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-sky-400 group-hover:text-sky-300 transition-colors">
                                  {exp.typology || "AML Finding"}
                                </span>
                                <span className="text-[10px] font-mono text-sky-400 bg-sky-950/60 px-2 py-0.5 rounded border border-sky-500/30">
                                  Inspect Evidence &rarr;
                                </span>
                              </div>
                              <p className="text-slate-300 leading-relaxed">{exp.explanation || exp.summary}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Tab 2: Execution Plan (Task 4.2 / Task 3.2) */}
                {activeTab === "plan" && (
                  <ExecutionPlanTimeline plan={queryResponse.execution_plan} trace={queryResponse.trace} />
                )}

                {/* Tab 3: Flagged Results Table (Task 4.3 & 4.4) */}
                {activeTab === "results" && (
                  <ResultsTable
                    flags={queryResponse.flags}
                    queryId={queryResponse.query_id}
                    onSelectFlag={openDrawerForFlag}
                  />
                )}

                {/* Tab 4: Telemetry & Trace Log */}
                {activeTab === "trace" && (
                  <div className="space-y-4 font-mono text-xs">
                    <div className="p-4 rounded-xl bg-slate-950 border border-white/10 space-y-2">
                      <div className="text-sky-400 font-bold text-sm">// Execution Trace Telemetry</div>
                      <pre className="text-slate-300 overflow-x-auto p-3 bg-black/40 rounded-lg text-[11px] leading-relaxed">
                        {JSON.stringify(queryResponse.trace, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Tab 5: Team Ownership & Slices */}
                {activeTab === "architecture" && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                    {/* Dev A */}
                    <div className="p-4 rounded-xl bg-slate-900/50 border border-purple-500/20 space-y-2">
                      <div className="text-purple-400 font-bold">Dev A &bull; Agent & Explainability Lead</div>
                      <p className="text-slate-400">Schemas, EDA profiling, Intent Parser (3.1), LLM Synthesizer (3.4), Typology Explanations (2.6), Execution Plan Timeline (4.2), Evidence Drawer (4.4).</p>
                    </div>

                    {/* Dev B */}
                    <div className="p-4 rounded-xl bg-slate-900/50 border border-sky-500/30 space-y-2">
                      <div className="text-sky-400 font-bold">Dev B &bull; Rules, Risk & Platform</div>
                      <p className="text-slate-400">FastAPI, SQLite Audit Store (1.4), Deterministic Detectors (2.3), Risk Fusion (2.5), Dynamic Planner (3.2), /query & /audit API (3.6), Dashboard UI.</p>
                    </div>

                    {/* Dev C */}
                    <div className="p-4 rounded-xl bg-slate-900/50 border border-emerald-500/20 space-y-2">
                      <div className="text-emerald-400 font-bold">Dev C &bull; Data, ML & Analytics</div>
                      <p className="text-slate-400">Data Loader (1.2), Stratified Sampler (1.3), Feature Engineering (2.2), Isolation Forest ML (2.4), Plan Executor (3.3).</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>

      {/* Explanation & Evidence Drawer (Task 4.4) */}
      <ExplanationEvidenceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        data={drawerData}
      />

      {/* Footer */}
      <footer className="border-t border-white/5 py-4 bg-[#090d16]/80 text-center text-xs text-slate-500">
        Argus AML Platform &bull; Built with FastAPI & Next.js &bull; Open-Source Financial Crime Detection Framework
      </footer>
    </div>
  );
}
