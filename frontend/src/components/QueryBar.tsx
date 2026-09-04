"use client";

import React, { useState } from "react";
import { Search, Zap, Sparkles, SlidersHorizontal, RefreshCw, Layers, ShieldCheck, Database } from "lucide-react";

export interface PresetScenario {
  id: string;
  label: string;
  query: string;
  tag: string;
  color: string;
  description: string;
}

export const DEMO_PRESETS: PresetScenario[] = [
  {
    id: "scenario_1",
    label: "1. Full Dataset Scan",
    query: "Analyse this dataset for suspicious activity",
    tag: "Full Pipeline (6 Tools)",
    color: "bg-sky-500/10 text-sky-400 border-sky-500/30 hover:bg-sky-500/20",
    description: "Executes complete investigative pipeline (EDA -> Features -> ML -> Rules -> Risk -> Explain).",
  },
  {
    id: "scenario_2",
    label: "2. Structuring Patterns (30d)",
    query: "Find structuring patterns in the last 30 days",
    tag: "Skips EDA & ML",
    color: "bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20",
    description: "Temporal filter, targeted rule detection, explicitly bypasses EDA & ML.",
  },
  {
    id: "scenario_3",
    label: "3. 10+ Txs Under $10,000",
    query: "Which customers made 10+ transactions under $10,000?",
    tag: "Skips ML",
    color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20",
    description: "Pure deterministic aggregation & threshold counting, no ML noise.",
  },
  {
    id: "scenario_4",
    label: "4. Customer 4521 Drill-Down",
    query: "Is customer 4521 suspicious?",
    tag: "Single Entity 360°",
    color: "bg-purple-500/10 text-purple-400 border-purple-500/30 hover:bg-purple-500/20",
    description: "Scoped counterparty profiling, pass-through detection, and on-demand ML scoring.",
  },
];

interface QueryBarProps {
  query: string;
  setQuery: (q: string) => void;
  onExecute: (queryText: string) => void;
  isLoading: boolean;
  isMockMode: boolean;
  setIsMockMode: (val: boolean) => void;
  normalSampleSize: number;
  setNormalSampleSize: (val: number) => void;
}

export const QueryBar: React.FC<QueryBarProps> = ({
  query,
  setQuery,
  onExecute,
  isLoading,
  isMockMode,
  setIsMockMode,
  normalSampleSize,
  setNormalSampleSize,
}) => {
  const [showFilters, setShowFilters] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    onExecute(query);
  };

  const handlePresetSelect = (preset: PresetScenario) => {
    setQuery(preset.query);
    onExecute(preset.query);
  };

  return (
    <div className="space-y-4">
      {/* Search Bar Input Container */}
      <form onSubmit={handleSubmit} className="glass-panel p-2.5 rounded-2xl shadow-2xl border border-white/10 relative">
        <div className="relative flex items-center">
          <Search className="absolute left-4 h-5 w-5 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
            placeholder="Ask an AML question (e.g., 'Find structuring patterns in the last 30 days')..."
            className="w-full bg-slate-950/70 text-slate-100 pl-12 pr-44 py-3.5 rounded-xl border border-white/5 focus:outline-none focus:border-sky-500/50 text-sm placeholder:text-slate-500 transition-all font-sans disabled:opacity-50"
          />

          {/* Action Buttons */}
          <div className="absolute right-2 flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              title="Toggle Sampling / Filter Options"
              className={`p-2 rounded-lg border transition-all text-xs flex items-center space-x-1 ${
                showFilters
                  ? "bg-sky-500/20 text-sky-400 border-sky-500/40"
                  : "bg-slate-900/60 text-slate-400 border-white/10 hover:text-slate-200"
              }`}
            >
              <SlidersHorizontal className="h-4 w-4" />
            </button>

            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-medium text-xs shadow-lg shadow-sky-500/25 transition-all flex items-center space-x-2 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  <span>Planning...</span>
                </>
              ) : (
                <>
                  <Zap className="h-3.5 w-3.5" />
                  <span>Investigate</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Optional Filter Controls Tray */}
        {showFilters && (
          <div className="mt-3 pt-3 border-t border-white/10 px-3 pb-1 flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex items-center space-x-3">
              <span className="text-slate-400 flex items-center space-x-1">
                <Database className="h-3.5 w-3.5 text-slate-400" />
                <span>Stratified Normal Sample:</span>
              </span>
              <select
                value={normalSampleSize}
                onChange={(e) => setNormalSampleSize(Number(e.target.value))}
                className="bg-slate-900 border border-white/10 text-slate-200 rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-sky-500"
              >
                <option value={50}>50 Normal + 100% Laundering</option>
                <option value={200}>200 Normal + 100% Laundering</option>
                <option value={500}>500 Normal + 100% Laundering</option>
                <option value={1000}>1,000 Normal + 100% Laundering</option>
              </select>
            </div>

            {/* Zero-Latency Judging Fallback Toggle */}
            <div className="flex items-center space-x-2.5 bg-slate-900/60 px-3 py-1.5 rounded-xl border border-white/5">
              <span className="text-slate-400">Execution Mode:</span>
              <button
                type="button"
                onClick={() => setIsMockMode(!isMockMode)}
                className={`text-[11px] font-medium px-2.5 py-0.5 rounded-full border transition-all flex items-center space-x-1 ${
                  isMockMode
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                    : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${isMockMode ? "bg-amber-400" : "bg-emerald-400"}`}></span>
                <span>{isMockMode ? "Zero-Latency Mock Fallback" : "Live Backend API"}</span>
              </button>
            </div>
          </div>
        )}

        {/* 4 Core Demo Scenario Pills */}
        <div className="mt-3 px-2 pt-1 flex flex-wrap items-center gap-2">
          <div className="flex items-center space-x-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
            <Sparkles className="h-3 w-3 text-sky-400" />
            <span>Core Demo Scenarios:</span>
          </div>
          {DEMO_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handlePresetSelect(preset)}
              disabled={isLoading}
              title={preset.description}
              className={`text-xs px-3 py-1.5 rounded-xl border transition-all flex items-center space-x-2 font-medium group ${preset.color} disabled:opacity-50`}
            >
              <span>{preset.label}</span>
              <span className="text-[10px] opacity-75 font-mono px-1.5 py-0.2 rounded bg-black/20 group-hover:opacity-100">
                {preset.tag}
              </span>
            </button>
          ))}
        </div>
      </form>

      {/* Loading Skeleton Indicator */}
      {isLoading && (
        <div className="glass-panel p-4 rounded-2xl border border-sky-500/30 animate-pulse space-y-3">
          <div className="flex items-center justify-between text-xs text-sky-400 font-medium">
            <div className="flex items-center space-x-2">
              <RefreshCw className="h-4 w-4 animate-spin text-sky-400" />
              <span>Agent Orchestrator decomposing query & building dynamic execution plan...</span>
            </div>
            <span className="font-mono text-slate-400">Processing AML tools</span>
          </div>
          <div className="grid grid-cols-4 gap-2">
            <div className="h-2 bg-sky-500/30 rounded-full animate-pulse"></div>
            <div className="h-2 bg-indigo-500/30 rounded-full animate-pulse delay-75"></div>
            <div className="h-2 bg-purple-500/30 rounded-full animate-pulse delay-150"></div>
            <div className="h-2 bg-emerald-500/30 rounded-full animate-pulse delay-300"></div>
          </div>
        </div>
      )}
    </div>
  );
};
