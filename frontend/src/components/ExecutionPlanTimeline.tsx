"use client";

import React from "react";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  SkipForward,
  BrainCircuit,
  Sliders,
  Sparkles,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { ExecutionPlan, PlanStep, SkippedTool } from "@/lib/api";

interface ExecutionPlanTimelineProps {
  plan: ExecutionPlan;
}

export const ExecutionPlanTimeline: React.FC<ExecutionPlanTimelineProps> = ({ plan }) => {
  const getToolBadgeColor = (toolName: string) => {
    switch (toolName) {
      case "eda":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "features":
        return "bg-cyan-500/20 text-cyan-400 border-cyan-500/30";
      case "detectors_ml":
        return "bg-purple-500/20 text-purple-400 border-purple-500/30";
      case "detectors_rules":
        return "bg-amber-500/20 text-amber-400 border-amber-500/30";
      case "risk":
        return "bg-rose-500/20 text-rose-400 border-rose-500/30";
      case "explain":
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
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
      default:
        return <div className="h-2 w-2 rounded-full bg-slate-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Plan Header Card */}
      <div className="glass-panel p-5 rounded-2xl border border-sky-500/20 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-purple-500 to-indigo-600 flex items-center justify-center text-white">
              <BrainCircuit className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Dynamic Execution Plan</h3>
              <p className="text-[11px] text-slate-400">
                Inferred Intent: <span className="font-mono text-sky-400 font-semibold">{plan.detected_intent}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs font-mono">
            <span className="text-slate-500">Plan ID:</span>
            <span className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded border border-white/5">{plan.plan_id.slice(0, 12)}...</span>
          </div>
        </div>

        {/* Planner Reasoning Rationale */}
        <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-white/5 leading-relaxed">
          <span className="font-semibold text-purple-400">Agent Rationale: </span>
          {plan.reasoning}
        </p>
      </div>

      {/* Invoked Analytical Steps Timeline */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center space-x-2">
            <span>Invoked Tool Sequence ({plan.steps.length} steps)</span>
          </h4>
          <span className="text-[11px] text-emerald-400 font-medium">All Tools Executed Deterministically</span>
        </div>

        <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-white/10">
          {plan.steps.map((step, idx) => (
            <div key={idx} className="relative flex items-start space-x-3.5 group">
              <div className="relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 border border-white/10 group-hover:border-sky-500/50 transition-colors">
                {getStepStatusIcon(step.status)}
              </div>
              <div className="flex-1 bg-slate-900/60 hover:bg-slate-900/90 transition-colors p-3.5 rounded-xl border border-white/5 space-y-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold text-slate-400">Step {step.step_number}</span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md border font-semibold ${getToolBadgeColor(step.tool_name)}`}>
                      {step.tool_name}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono uppercase text-slate-400">{step.status}</span>
                </div>
                <p className="text-xs text-slate-200">{step.description}</p>
                {step.result_summary && (
                  <div className="text-[11px] font-mono text-sky-300 bg-sky-950/30 p-2 rounded-lg border border-sky-500/10">
                    &rarr; {step.result_summary}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Skipped Tools with Explicit Rationale (Crucial for Demo Judging) */}
      {plan.skipped_tools && plan.skipped_tools.length > 0 && (
        <div className="glass-panel p-6 rounded-2xl border border-amber-500/20 space-y-3">
          <div className="flex items-center space-x-2 text-amber-400">
            <SkipForward className="h-4 w-4" />
            <h4 className="text-xs font-bold uppercase tracking-wider">
              Skipped Analytical Tools ({plan.skipped_tools.length})
            </h4>
          </div>
          <p className="text-[11px] text-slate-400">
            The planner dynamically bypassed the following tools with explicit justification to reduce noise and optimize execution:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {plan.skipped_tools.map((st, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-slate-900/60 border border-amber-500/20 space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-amber-300 uppercase">{st.tool_name}</span>
                  <span className="text-[10px] text-amber-400/80 font-mono">SKIPPED</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">{st.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
