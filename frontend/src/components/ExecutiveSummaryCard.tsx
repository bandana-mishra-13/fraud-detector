"use client";

import React from "react";
import { Sparkles, CheckCircle2, ShieldAlert, AlertCircle, FileText, ExternalLink, Link2 } from "lucide-react";
import { SynthesizedResult, RiskResult } from "@/lib/api";

interface ExecutiveSummaryCardProps {
  synthesizedResult?: SynthesizedResult | null;
  riskResult?: RiskResult | null;
}

export const ExecutiveSummaryCard: React.FC<ExecutiveSummaryCardProps> = ({
  synthesizedResult,
  riskResult,
}) => {
  if (!synthesizedResult && !riskResult) {
    return null;
  }

  return (
    <div className="glass-panel p-6 rounded-2xl border border-sky-500/20 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/10">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-sky-500 via-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-sky-500/20">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">Executive Compliance Summary</h3>
            <p className="text-xs text-slate-400">LLM-Synthesized Findings Grounded on Deterministic Tool Evidence</p>
          </div>
        </div>

        {riskResult && (
          <div className="flex items-center space-x-3 bg-slate-900/80 px-4 py-2 rounded-xl border border-white/10">
            <div className="text-right">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Composite Risk</div>
              <div className="text-sm font-extrabold text-white">
                Tier: <span className="text-sky-400">{riskResult.risk_tier}</span> ({riskResult.risk_score.toFixed(4)})
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Narrative Executive Summary */}
      {synthesizedResult?.executive_summary && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Investigation Overview</h4>
          <p className="text-sm text-slate-200 leading-relaxed bg-slate-900/60 p-4 rounded-xl border border-white/5 font-sans">
            {synthesizedResult.executive_summary}
          </p>
        </div>
      )}

      {/* Key Findings List */}
      {synthesizedResult?.key_findings && synthesizedResult.key_findings.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Key AML Findings & Evidence</h4>
          <div className="grid grid-cols-1 gap-2.5">
            {synthesizedResult.key_findings.map((finding, idx) => (
              <div
                key={idx}
                className="flex items-start space-x-3 p-3 rounded-xl bg-slate-900/40 border border-white/5 text-xs text-slate-200"
              >
                <CheckCircle2 className="h-4 w-4 text-sky-400 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{finding}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cited Transaction IDs */}
      {synthesizedResult?.cited_transaction_ids && synthesizedResult.cited_transaction_ids.length > 0 && (
        <div className="space-y-2 pt-1">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
            <Link2 className="h-3.5 w-3.5 text-sky-400" />
            <span>Grounded Transaction Citations ({synthesizedResult.cited_transaction_ids.length})</span>
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {synthesizedResult.cited_transaction_ids.map((txId) => (
              <span
                key={txId}
                className="font-mono text-xs text-sky-300 bg-sky-950/40 border border-sky-500/30 px-2.5 py-1 rounded-lg font-medium"
              >
                {txId}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Limitations / Disclosures */}
      {synthesizedResult?.limitations && synthesizedResult.limitations.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-white/5">
          <h4 className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">
            Investigative Scope & Disclosures
          </h4>
          <ul className="list-disc list-inside space-y-1 text-xs text-slate-400">
            {synthesizedResult.limitations.map((lim, idx) => (
              <li key={idx} className="leading-relaxed">
                {lim}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
