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
  ChevronRight,
} from "lucide-react";
import { checkBackendHealth, HealthStatus, API_BASE_URL } from "@/lib/api";

export default function Home() {
  const [health, setHealth] = useState<HealthStatus>({ status: "loading" });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [queryInput, setQueryInput] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "plan" | "results" | "analytics">("overview");

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

  const presetQueries = [
    {
      label: "Full Dataset Anomaly Scan",
      query: "Analyse this dataset for suspicious activity and high-risk AML typologies",
      tag: "All Tools",
      color: "bg-sky-500/10 text-sky-400 border-sky-500/30",
    },
    {
      label: "Structuring Pattern (30d)",
      query: "Find structuring patterns and sub-$10,000 threshold deposits in the last 30 days",
      tag: "Rule Only",
      color: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    },
    {
      label: "High Velocity Smurfing",
      query: "Identify accounts with 10+ rapid fan-in transactions within 24 hours",
      tag: "Rule + Graph",
      color: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    },
    {
      label: "Entity Risk Drill-Down",
      query: "Is customer account #4521 suspicious? Run counterparty and anomaly drill-down",
      tag: "Single Entity",
      color: "bg-purple-500/10 text-purple-400 border-purple-500/30",
    },
  ];

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#090d16]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-sky-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <ShieldAlert className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold tracking-tight text-lg text-white">ARGUS</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/30 font-mono font-medium">
                  AML v0.1.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">Agentic Anti-Money Laundering & Risk Platform</p>
            </div>
          </div>

          {/* Backend Status Indicator */}
          <div className="flex items-center space-x-3">
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
                  ? `Backend Online (${health.latencyMs}ms)`
                  : health.status === "loading"
                  ? "Connecting..."
                  : "Backend Offline"}
              </span>
            </div>

            <button
              onClick={runHealthCheck}
              disabled={isRefreshing}
              title="Refresh backend status"
              className="p-1.5 rounded-lg border border-white/10 hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            </button>

            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border border-white/10 hover:bg-slate-800/60 text-xs text-slate-300 transition-colors"
            >
              <span>FastAPI Docs</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero & Query Bar (Phase 4.1 Preview) */}
        <section className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                Intelligent AML Investigation & Risk Fusion
              </h1>
              <p className="text-sm text-slate-400 mt-1 max-w-2xl">
                Dynamic query decomposition, deterministic rule engines, Isolation Forest ML anomaly scoring, and typology-grounded explainability.
              </p>
            </div>
            <div className="flex items-center space-x-2 text-xs font-mono text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-white/5">
              <span className="text-slate-500">Target API:</span>
              <span className="text-sky-400">{API_BASE_URL}</span>
            </div>
          </div>

          {/* Natural Language Query Bar */}
          <div className="glass-panel p-2 rounded-2xl shadow-2xl border border-white/10">
            <div className="relative flex items-center">
              <Search className="absolute left-4 h-5 w-5 text-slate-400" />
              <input
                type="text"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="Ask an AML investigation question (e.g. 'Identify structuring under $10,000 in past 30 days')..."
                className="w-full bg-slate-950/60 text-slate-100 pl-12 pr-32 py-3.5 rounded-xl border border-white/5 focus:outline-none focus:border-sky-500/50 text-sm placeholder:text-slate-500 transition-all font-sans"
              />
              <button
                onClick={() => {}}
                className="absolute right-2 px-5 py-2 rounded-lg bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-medium text-xs shadow-md shadow-sky-500/20 transition-all flex items-center space-x-1.5"
              >
                <Zap className="h-3.5 w-3.5" />
                <span>Run Agent</span>
              </button>
            </div>

            {/* Scenario Preset Pills */}
            <div className="mt-3 px-2 pt-1 pb-1 flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mr-1">
                Demo Presets:
              </span>
              {presetQueries.map((preset, idx) => (
                <button
                  key={idx}
                  onClick={() => setQueryInput(preset.query)}
                  className={`text-xs px-2.5 py-1 rounded-lg border transition-all hover:brightness-125 flex items-center space-x-1.5 ${preset.color}`}
                >
                  <span>{preset.label}</span>
                  <span className="opacity-60 text-[10px]">({preset.tag})</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* System Diagnostics & Phase 0 Status Card */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Health & API Card */}
          <div className="glass-panel p-6 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Server className="h-5 w-5 text-sky-400" />
                <h3 className="text-sm font-semibold text-white">Backend Health</h3>
              </div>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase ${
                  health.status === "ok"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                }`}
              >
                {health.status}
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Endpoint</span>
                <span className="font-mono text-slate-200">GET /health</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Service</span>
                <span className="text-slate-200 font-medium">{health.service || "Argus AML"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Version</span>
                <span className="font-mono text-slate-200">{health.version || "0.1.0"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Roundtrip Latency</span>
                <span className="font-mono text-sky-400">{health.latencyMs ? `${health.latencyMs} ms` : "—"}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Environment</span>
                <span className="text-slate-200 capitalize">{health.environment || "Development"}</span>
              </div>
            </div>

            {health.status === "ok" ? (
              <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-950/20 border border-emerald-500/20 p-2.5 rounded-xl">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>FastAPI backend operational and responding to CORS requests.</span>
              </div>
            ) : health.status === "loading" ? (
              <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-900/40 p-2.5 rounded-xl border border-white/5">
                <Activity className="h-4 w-4 animate-spin text-sky-400" />
                <span>Checking backend connection on port 8000...</span>
              </div>
            ) : (
              <div className="space-y-2 text-xs text-rose-400 bg-rose-950/30 border border-rose-500/30 p-2.5 rounded-xl">
                <div className="flex items-center space-x-2 font-medium">
                  <XCircle className="h-4 w-4 shrink-0" />
                  <span>Backend unreachable at {API_BASE_URL}</span>
                </div>
                <p className="text-[11px] text-slate-400 font-mono">
                  Run: <code>cd backend; uvicorn app.main:app --port 8000</code>
                </p>
              </div>
            )}
          </div>

          {/* Architecture & Team Slices */}
          <div className="glass-panel p-6 rounded-2xl space-y-4 md:col-span-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Layers className="h-5 w-5 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">System Architecture & Team Slices</h3>
              </div>
              <span className="text-xs text-slate-400">Phase 0 Foundations Ready</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
              {/* Dev A Card */}
              <div className="p-3.5 rounded-xl bg-slate-900/50 border border-purple-500/20 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-purple-400">Dev A</span>
                  <BrainCircuit className="h-4 w-4 text-purple-400" />
                </div>
                <h4 className="text-xs font-semibold text-slate-200">Agent & Explainability Lead</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Pydantic Schemas, Intent Parser, LLM Synthesizer, Typology Explainer, Dynamic Execution Plan UI.
                </p>
                <div className="text-[10px] font-mono text-purple-300/80 bg-purple-500/10 px-2 py-0.5 rounded inline-block">
                  Phase 1.1, 2.1, 2.6, 3.1
                </div>
              </div>

              {/* Dev B Card (Current Lead) */}
              <div className="p-3.5 rounded-xl bg-slate-900/50 border border-sky-500/30 space-y-2 relative overflow-hidden">
                <div className="absolute top-0 right-0 h-1.5 w-full bg-sky-500"></div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-sky-400">Dev B (Platform & Rules)</span>
                  <SlidersHorizontal className="h-4 w-4 text-sky-400" />
                </div>
                <h4 className="text-xs font-semibold text-slate-200">Rules, Risk & Platform</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  FastAPI Scaffold, Deterministic Rules (Structuring, Smurfing), Risk Fusion Engine, SQLite Audit Store, Dashboard UI.
                </p>
                <div className="text-[10px] font-mono text-sky-300/80 bg-sky-500/10 px-2 py-0.5 rounded inline-block">
                  Phase 0.3, 0.4, 1.4, 2.3, 2.5
                </div>
              </div>

              {/* Dev C Card */}
              <div className="p-3.5 rounded-xl bg-slate-900/50 border border-emerald-500/20 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-400">Dev C</span>
                  <BarChart3 className="h-4 w-4 text-emerald-400" />
                </div>
                <h4 className="text-xs font-semibold text-slate-200">Data, ML & Analytics</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Data Pipeline & Stratified Sampler, Feature Engineering, Isolation Forest ML Detector, Plan Executor & Tracing.
                </p>
                <div className="text-[10px] font-mono text-emerald-300/80 bg-emerald-500/10 px-2 py-0.5 rounded inline-block">
                  Phase 0.5, 1.2, 2.2, 2.4, 3.3
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Phase 4 Scaffold Preview Tabs */}
        <section className="glass-panel rounded-2xl border border-white/10 overflow-hidden">
          <div className="flex border-b border-white/10 px-6 pt-4 gap-6 text-sm font-medium">
            <button
              onClick={() => setActiveTab("overview")}
              className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                activeTab === "overview"
                  ? "border-sky-500 text-sky-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Activity className="h-4 w-4" />
              <span>Pipeline Overview</span>
            </button>
            <button
              onClick={() => setActiveTab("plan")}
              className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                activeTab === "plan"
                  ? "border-sky-500 text-sky-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <BrainCircuit className="h-4 w-4" />
              <span>Dynamic Execution Plan</span>
            </button>
            <button
              onClick={() => setActiveTab("results")}
              className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                activeTab === "results"
                  ? "border-sky-500 text-sky-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <ShieldAlert className="h-4 w-4" />
              <span>Detection Results Table</span>
            </button>
            <button
              onClick={() => setActiveTab("analytics")}
              className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
                activeTab === "analytics"
                  ? "border-sky-500 text-sky-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <BarChart3 className="h-4 w-4" />
              <span>Analytics & Drill-Down</span>
            </button>
          </div>

          <div className="p-6">
            {activeTab === "overview" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-white">End-to-End AML Workflow</h4>
                  <span className="text-xs text-slate-400">Orchestrator Contract</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
                    <div className="h-7 w-7 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold">1</div>
                    <h5 className="font-semibold text-slate-200">NL Intent Parsing</h5>
                    <p className="text-slate-400">Extracts entities, target rules, time windows, and intent from analyst query.</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
                    <div className="h-7 w-7 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold">2</div>
                    <h5 className="font-semibold text-slate-200">Dynamic Planning</h5>
                    <p className="text-slate-400">Decides which deterministic tools to invoke vs. skip with transparent reasoning.</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
                    <div className="h-7 w-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">3</div>
                    <h5 className="font-semibold text-slate-200">Hybrid Risk Fusion</h5>
                    <p className="text-slate-400">Combines rule detectors + Isolation Forest ML score into unified risk tiers (High/Med/Low).</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 space-y-2">
                    <div className="h-7 w-7 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold">4</div>
                    <h5 className="font-semibold text-slate-200">Grounded Synthesis</h5>
                    <p className="text-slate-400">Generates executive AML summary citing exact flagged transaction IDs and rules.</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "plan" && (
              <div className="p-8 text-center text-slate-400 space-y-2">
                <BrainCircuit className="h-8 w-8 text-purple-400 mx-auto animate-pulse" />
                <p className="text-sm font-medium text-slate-300">Execution Plan Panel (Phase 4.2)</p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Will render interactive timeline showing tools invoked vs skipped (e.g. EDA skipped for structuring rule queries).
                </p>
              </div>
            )}

            {activeTab === "results" && (
              <div className="p-8 text-center text-slate-400 space-y-2">
                <ShieldAlert className="h-8 w-8 text-sky-400 mx-auto" />
                <p className="text-sm font-medium text-slate-300">Results Table & Risk Badges (Phase 4.3)</p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Will render flagged transactions, risk tier badges (High/Med/Low), counterparty links, and feedback actions.
                </p>
              </div>
            )}

            {activeTab === "analytics" && (
              <div className="p-8 text-center text-slate-400 space-y-2">
                <BarChart3 className="h-8 w-8 text-emerald-400 mx-auto" />
                <p className="text-sm font-medium text-slate-300">Analytics & Distribution Charts (Phase 4.5)</p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Will render transaction amount histograms, risk tier donuts, and velocity trends using Recharts.
                </p>
              </div>
            )}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-4 bg-[#090d16]/50 text-center text-xs text-slate-500">
        Argus AML Platform &bull; Built with FastAPI & Next.js &bull; Generic Financial Crime Detection Framework
      </footer>
    </div>
  );
}
