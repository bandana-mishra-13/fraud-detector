"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  SkipForward,
  BrainCircuit,
  ArrowRight,
  ShieldAlert,
  BarChart2,
  Cpu,
  Zap,
  FileText,
  Filter,
  Calendar,
  DollarSign,
  UserCheck,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Info,
  Hash,
} from "lucide-react";
import { ExecutionPlan, PlanStep, SkippedTool, ExecutionTrace } from "@/lib/api";

interface ExecutionPlanTimelineProps {
  plan: ExecutionPlan;
  trace?: ExecutionTrace | null;
}

const ALL_PIPELINE_TOOLS = [
  { id: "eda", name: "EDA Profiling", description: "Exploratory data analysis & baseline stats" },
  { id: "features", name: "Feature Eng.", description: "Rolling velocities & network graph metrics" },
  { id: "detectors_ml", name: "ML Detector", description: "Unsupervised Isolation Forest anomaly scoring" },
  { id: "detectors_rules", name: "Rule Engine", description: "Deterministic AML typology pattern rules" },
  { id: "risk", name: "Risk Fusion", description: "Hybrid heuristic & ML risk score fusion" },
  { id: "explain", name: "Explainability", description: "Typology-tied natural language evidence citations" },
];

export const ExecutionPlanTimeline: React.FC<ExecutionPlanTimelineProps> = ({ plan, trace }) => {
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const toggleStepExpanded = (stepNumber: number) => {
    setExpandedStep(expandedStep === stepNumber ? null : stepNumber);
  };

  const getToolConfig = (toolName: string) => {
    switch (toolName) {
      case "eda":
        return {
          label: "EDA Profiling",
          icon: <BarChart2 className="h-4 w-4 text-blue-400" />,
          colorClass: "bg-blue-500/20 text-blue-300 border-blue-500/40",
          glowClass: "shadow-blue-500/10",
        };
      case "features":
        return {
          label: "Feature Eng.",
          icon: <Cpu className="h-4 w-4 text-cyan-400" />,
          colorClass: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40",
          glowClass: "shadow-cyan-500/10",
        };
      case "detectors_ml":
        return {
          label: "ML Anomaly Detector",
          icon: <BrainCircuit className="h-4 w-4 text-purple-400" />,
          colorClass: "bg-purple-500/20 text-purple-300 border-purple-500/40",
          glowClass: "shadow-purple-500/10",
        };
      case "detectors_rules":
        return {
          label: "Rule Engine",
          icon: <ShieldAlert className="h-4 w-4 text-amber-400" />,
          colorClass: "bg-amber-500/20 text-amber-300 border-amber-500/40",
          glowClass: "shadow-amber-500/10",
        };
      case "risk":
        return {
          label: "Risk Fusion",
          icon: <Zap className="h-4 w-4 text-rose-400" />,
          colorClass: "bg-rose-500/20 text-rose-300 border-rose-500/40",
          glowClass: "shadow-rose-500/10",
        };
      case "explain":
        return {
          label: "Explainability Tool",
          icon: <FileText className="h-4 w-4 text-emerald-400" />,
          colorClass: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
          glowClass: "shadow-emerald-500/10",
        };
      default:
        return {
          label: toolName,
          icon: <Activity className="h-4 w-4 text-slate-400" />,
          colorClass: "bg-slate-800 text-slate-300 border-slate-700",
          glowClass: "",
        };
    }
  };

  const getStepStatusIcon = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case "IN_PROGRESS":
        return <Clock className="h-4 w-4 text-sky-400 animate-spin" />;
      case "FAILED":
        return <AlertCircle className="h-4 w-4 text-rose-400" />;
      case "SKIPPED":
        return <SkipForward className="h-4 w-4 text-amber-400" />;
      default:
        return <div className="h-2 w-2 rounded-full bg-slate-500" />;
    }
  };

  const formatFilterDisplay = (key: string, value: any) => {
    if (key === "time_window_days" || key === "time_window") {
      return {
        icon: <Calendar className="h-3.5 w-3.5 text-sky-400" />,
        label: "Time Window",
        value: typeof value === "number" ? `${value} Days` : String(value),
      };
    }
    if (key === "pattern") {
      return {
        icon: <Filter className="h-3.5 w-3.5 text-purple-400" />,
        label: "Target Pattern",
        value: String(value),
      };
    }
    if (key === "min_transaction_count") {
      return {
        icon: <Hash className="h-3.5 w-3.5 text-cyan-400" />,
        label: "Min Transactions",
        value: `${value}+`,
      };
    }
    if (key === "max_transaction_amount" || key === "min_amount") {
      return {
        icon: <DollarSign className="h-3.5 w-3.5 text-emerald-400" />,
        label: key.includes("max") ? "Max Amount" : "Min Amount",
        value: `$${Number(value).toLocaleString()}`,
      };
    }
    if (key === "rules") {
      return {
        icon: <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />,
        label: "Target Rules",
        value: Array.isArray(value) ? value.join(", ") : String(value),
      };
    }
    return {
      icon: <Layers className="h-3.5 w-3.5 text-indigo-400" />,
      label: key.replace(/_/g, " "),
      value: typeof value === "object" ? JSON.stringify(value) : String(value),
    };
  };

  const invokedToolsSet = new Set(plan.invoked_tools || []);
  const skippedToolsMap = new Map((plan.skipped_tools || []).map((st) => [st.tool_name, st.reason]));

  return (
    <div className="space-y-6">
      {/* 1. Header Card: Intent, Reasoning, Active Filters & Target Entities */}
      <div className="glass-panel p-6 rounded-2xl border border-purple-500/20 shadow-xl space-y-4">
        {/* Top Header Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-white/10">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-sky-500 flex items-center justify-center text-white shadow-lg shadow-purple-500/25">
              <BrainCircuit className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-white tracking-tight">Dynamic Execution Plan</h3>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Dev A Agent Engine
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Query Intent:{" "}
                <span className="font-mono text-sky-400 font-bold uppercase tracking-wider">{plan.detected_intent}</span>
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <div className="bg-slate-900/80 px-3 py-1 rounded-lg border border-white/10 text-slate-300">
              <span className="text-slate-500">Plan ID:</span>{" "}
              <span className="text-sky-300 font-semibold">{plan.plan_id.slice(0, 8)}...</span>
            </div>
            <div className="bg-slate-900/80 px-3 py-1 rounded-lg border border-white/10 text-slate-300">
              <span className="text-slate-500">Created:</span>{" "}
              <span className="text-slate-300">{new Date(plan.created_at).toLocaleTimeString()}</span>
            </div>
          </div>
        </div>

        {/* Planner Reasoning Rationale */}
        <div className="p-4 rounded-xl bg-slate-950/70 border border-white/5 space-y-1.5">
          <div className="flex items-center space-x-2 text-xs font-bold text-purple-400">
            <Sparkles className="h-4 w-4 text-purple-400" />
            <span>LLM Agent Optimization Rationale</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-sans">{plan.reasoning}</p>
        </div>

        {/* Active Filters & Target Entities Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* Target Entities */}
          <div className="p-3.5 rounded-xl bg-slate-900/50 border border-white/5 space-y-2">
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <UserCheck className="h-3.5 w-3.5 text-sky-400" />
              <span>Target Entities Investigated</span>
            </div>
            {plan.target_entities && plan.target_entities.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {plan.target_entities.map((entity, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center space-x-1.5 text-xs font-mono px-3 py-1 rounded-lg bg-sky-500/15 text-sky-300 border border-sky-500/30 font-semibold"
                  >
                    <span>Account: {entity}</span>
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-xs text-slate-500 italic">No specific target entity constraint (Global dataset scan)</span>
            )}
          </div>

          {/* Active Filters */}
          <div className="p-3.5 rounded-xl bg-slate-900/50 border border-white/5 space-y-2">
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <Filter className="h-3.5 w-3.5 text-purple-400" />
              <span>Active Query Filters & Parameters</span>
            </div>
            {plan.active_filters && Object.keys(plan.active_filters).length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {Object.entries(plan.active_filters).map(([k, v], idx) => {
                  const filterInfo = formatFilterDisplay(k, v);
                  return (
                    <div
                      key={idx}
                      className="inline-flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-lg bg-purple-500/15 text-purple-200 border border-purple-500/30 font-mono"
                    >
                      {filterInfo.icon}
                      <span className="text-slate-400">{filterInfo.label}:</span>
                      <span className="font-bold text-white">{filterInfo.value}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <span className="text-xs text-slate-500 italic">No explicit filter constraints applied</span>
            )}
          </div>
        </div>
      </div>

      {/* 2. Visual Tools Invoked vs Skipped Pipeline Overview Bar */}
      <div className="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center space-x-2">
            <Layers className="h-4 w-4 text-sky-400" />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider">
              AML Tool Pipeline Matrix ({plan.invoked_tools.length} Invoked &bull; {plan.skipped_tools.length} Skipped)
            </h4>
          </div>
          <div className="flex items-center space-x-3 text-xs">
            <span className="flex items-center space-x-1 text-emerald-400 font-mono">
              <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
              <span>Invoked</span>
            </span>
            <span className="flex items-center space-x-1 text-amber-400 font-mono">
              <span className="h-2 w-2 rounded-full bg-amber-400"></span>
              <span>Skipped</span>
            </span>
          </div>
        </div>

        {/* 6-Step Pipeline Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 pt-1">
          {ALL_PIPELINE_TOOLS.map((tool) => {
            const isInvoked = invokedToolsSet.has(tool.id);
            const isSkipped = skippedToolsMap.has(tool.id);
            const config = getToolConfig(tool.id);
            const timing = trace?.execution_timings_ms?.[tool.id];

            return (
              <div
                key={tool.id}
                className={`p-3 rounded-xl border transition-all text-left flex flex-col justify-between space-y-2 ${
                  isInvoked
                    ? "bg-slate-900/80 border-sky-500/30 shadow-lg shadow-sky-500/5"
                    : isSkipped
                    ? "bg-slate-950/60 border-amber-500/20 opacity-80"
                    : "bg-slate-950/30 border-white/5 opacity-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="p-1.5 rounded-lg bg-slate-800/80">{config.icon}</div>
                  {isInvoked ? (
                    <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      INVOKED
                    </span>
                  ) : isSkipped ? (
                    <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      SKIPPED
                    </span>
                  ) : (
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-500">
                      OFFLINE
                    </span>
                  )}
                </div>

                <div>
                  <div className="text-xs font-bold text-white truncate">{tool.name}</div>
                  <div className="text-[10px] text-slate-400 line-clamp-1">{tool.description}</div>
                </div>

                {timing !== undefined && isInvoked && (
                  <div className="text-[10px] font-mono text-sky-400 pt-1 border-t border-white/5">
                    {timing.toFixed(1)} ms
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Invoked Analytical Tool Sequence Timeline */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <Activity className="h-4 w-4 text-emerald-400" />
            <span>Invoked Step Sequence ({plan.steps.length} Steps Executed)</span>
          </h4>
          <span className="text-[11px] text-emerald-400 font-mono font-semibold bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            Deterministic Output Guarantee
          </span>
        </div>

        <div className="space-y-4 relative before:absolute before:inset-0 before:left-4 before:w-0.5 before:bg-gradient-to-b before:from-sky-500/50 before:via-purple-500/50 before:to-emerald-500/50">
          {plan.steps.map((step) => {
            const config = getToolConfig(step.tool_name);
            const isExpanded = expandedStep === step.step_number;
            const hasParameters = step.parameters && Object.keys(step.parameters).length > 0;
            const timing = trace?.execution_timings_ms?.[step.tool_name];

            return (
              <div key={step.step_number} className="relative flex items-start space-x-4 group">
                {/* Timeline Step Bullet */}
                <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-900 border border-white/15 group-hover:border-sky-500/50 transition-all shadow-md">
                  {getStepStatusIcon(step.status)}
                </div>

                {/* Step Card */}
                <div className="flex-1 bg-slate-900/70 hover:bg-slate-900/90 transition-all p-4 rounded-xl border border-white/10 space-y-2.5 shadow-md">
                  {/* Step Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2.5">
                      <span className="text-xs font-mono font-extrabold text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                        Step {step.step_number}
                      </span>
                      <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded-lg border flex items-center space-x-1.5 ${config.colorClass}`}>
                        {config.icon}
                        <span>{config.label}</span>
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      {timing !== undefined && (
                        <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
                          {timing.toFixed(1)} ms
                        </span>
                      )}
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-semibold">
                        {step.status}
                      </span>
                      {hasParameters && (
                        <button
                          onClick={() => toggleStepExpanded(step.step_number)}
                          className="p-1 rounded bg-slate-800 text-slate-400 hover:text-white transition-colors"
                          title="Toggle step parameters"
                        >
                          {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Step Description */}
                  <p className="text-xs text-slate-200 leading-relaxed">{step.description}</p>

                  {/* Result Summary Callout */}
                  {step.result_summary && (
                    <div className="text-xs font-mono text-sky-300 bg-sky-950/40 p-2.5 rounded-lg border border-sky-500/20 flex items-start space-x-2">
                      <ArrowRight className="h-4 w-4 text-sky-400 shrink-0 mt-0.5" />
                      <span className="leading-snug">{step.result_summary}</span>
                    </div>
                  )}

                  {/* Expandable Parameters Drawer */}
                  {hasParameters && isExpanded && (
                    <div className="pt-2 border-t border-white/5 text-xs font-mono space-y-1">
                      <span className="text-slate-500 text-[11px]">Invocation Parameters:</span>
                      <pre className="p-2.5 rounded-lg bg-black/50 text-purple-300 overflow-x-auto text-[11px]">
                        {JSON.stringify(step.parameters, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Skipped Tools Panel with Justification (Critical for Demo Judging) */}
      {plan.skipped_tools && plan.skipped_tools.length > 0 && (
        <div className="glass-panel p-6 rounded-2xl border border-amber-500/20 shadow-xl space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-amber-500/10">
            <div className="flex items-center space-x-2 text-amber-400">
              <SkipForward className="h-5 w-5" />
              <h4 className="text-xs font-bold uppercase tracking-wider">
                Dynamically Skipped Tools ({plan.skipped_tools.length} Bypassed)
              </h4>
            </div>
            <span className="text-[11px] font-mono text-amber-300 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20">
              Latency & Noise Optimization
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            The agentic planner dynamically bypassed the following tools for this specific query intent to eliminate redundant computation, minimize false positive noise, and optimize latency:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {plan.skipped_tools.map((st, idx) => {
              const config = getToolConfig(st.tool_name);
              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-900/80 border border-amber-500/20 space-y-2 text-xs shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 font-mono font-bold text-amber-300">
                      {config.icon}
                      <span className="uppercase">{config.label}</span>
                    </div>
                    <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                      SKIPPED
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">{st.reason}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
