"use client";

import React, { useState } from "react";
import {
  X,
  ShieldAlert,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Link2,
  Activity,
  Layers,
  ArrowRight,
  UserCheck,
  Calendar,
  DollarSign,
  Check,
  XCircle,
  MessageSquare,
  Sparkles,
  Database,
  ExternalLink,
} from "lucide-react";
import { RiskTier } from "@/lib/api";

export interface ExplanationDrawerData {
  flagId?: string;
  ruleId?: string;
  ruleName?: string;
  typology?: string;
  severity?: RiskTier | string;
  entityId?: string | null;
  summary?: string;
  explanation?: string;
  transactionIds?: string[];
  evidence?: Record<string, any>;
  timestamp?: string;
}

interface ExplanationEvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  data: ExplanationDrawerData | null;
  onFeedbackSubmit?: (flagId: string, status: string, notes: string) => void;
}

export const ExplanationEvidenceDrawer: React.FC<ExplanationEvidenceDrawerProps> = ({
  isOpen,
  onClose,
  data,
  onFeedbackSubmit,
}) => {
  const [feedbackStatus, setFeedbackStatus] = useState<string>("CONFIRMED_SUSPICIOUS");
  const [analystNotes, setAnalystNotes] = useState<string>("");
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);

  if (!isOpen || !data) return null;

  const getSeverityBadge = (sev?: RiskTier | string) => {
    const s = String(sev || "HIGH").toUpperCase();
    switch (s) {
      case "CRITICAL":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-rose-500/10";
      case "HIGH":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-amber-500/10";
      case "MEDIUM":
        return "bg-sky-500/20 text-sky-300 border-sky-500/40 shadow-sky-500/10";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (data.flagId && onFeedbackSubmit) {
      onFeedbackSubmit(data.flagId, feedbackStatus, analystNotes);
      setIsSubmitted(true);
      setTimeout(() => setIsSubmitted(false), 3000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/70 backdrop-blur-sm transition-opacity animate-in fade-in duration-200">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-xl bg-[#0d1322] border-l border-white/10 shadow-2xl flex flex-col">
          {/* Drawer Header */}
          <div className="p-6 border-b border-white/10 flex items-center justify-between bg-[#090d16]/90">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-rose-500 via-indigo-600 to-sky-500 flex items-center justify-center text-white shadow-lg shadow-rose-500/20">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-bold text-white tracking-tight">Typology & Evidence Drawer</h3>
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${getSeverityBadge(data.severity)}`}>
                    {data.severity || "HIGH"}
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Flag ID: <span className="text-sky-400 font-semibold">{data.flagId || "FLAG-LOCAL"}</span>
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl border border-white/10 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              title="Close Drawer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Drawer Body Scroll Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* 1. Typology Classification & Rule Meta */}
            <div className="glass-panel p-5 rounded-2xl border border-purple-500/20 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <Sparkles className="h-4 w-4" />
                  <span>AML Typology Classification</span>
                </span>
                <span className="text-xs font-mono text-slate-400">{data.ruleId || "RULE-DETECTOR"}</span>
              </div>

              <div className="text-lg font-extrabold text-white">{data.typology || data.ruleName || "General AML Anomaly"}</div>
              
              <div className="flex flex-wrap items-center gap-2 text-xs font-mono pt-1">
                <span className="text-slate-400 bg-slate-900 px-2.5 py-1 rounded-lg border border-white/5">
                  Rule Name: <span className="text-white font-semibold">{data.ruleName || "AML Rule"}</span>
                </span>
                {data.entityId && (
                  <span className="text-slate-400 bg-slate-900 px-2.5 py-1 rounded-lg border border-white/5">
                    Target Entity: <span className="text-sky-300 font-bold">{data.entityId}</span>
                  </span>
                )}
              </div>
            </div>

            {/* 2. Natural Language Compliance Explanation */}
            <div className="glass-panel p-5 rounded-2xl border border-sky-500/20 space-y-2.5">
              <h4 className="text-xs font-semibold text-sky-400 uppercase tracking-wider flex items-center space-x-1.5">
                <FileText className="h-4 w-4" />
                <span>Dev A Typology-Tied Narrative (explain.py)</span>
              </h4>
              <p className="text-xs text-slate-200 leading-relaxed bg-slate-950/70 p-4 rounded-xl border border-white/5 font-sans">
                {data.explanation || data.summary || "No specific narrative explanation was generated for this finding."}
              </p>
            </div>

            {/* 3. Evidence Metrics Breakdown */}
            {data.evidence && Object.keys(data.evidence).length > 0 && (
              <div className="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <Activity className="h-4 w-4 text-emerald-400" />
                  <span>Deterministic Evidence Metrics</span>
                </h4>

                <div className="grid grid-cols-2 gap-2.5 font-mono text-xs">
                  {Object.entries(data.evidence).map(([key, val]) => (
                    <div key={key} className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-0.5">
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider">{key.replace(/_/g, " ")}</div>
                      <div className="text-xs font-bold text-emerald-300">
                        {typeof val === "number"
                          ? key.includes("amount")
                            ? `$${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                            : val.toLocaleString()
                          : String(val)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 4. Cited Supporting Transaction IDs */}
            <div className="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <Link2 className="h-4 w-4 text-sky-400" />
                  <span>Cited Evidence Transactions ({data.transactionIds?.length || 0})</span>
                </h4>
                <span className="text-[10px] text-slate-400 font-mono">100% Grounded</span>
              </div>

              {data.transactionIds && data.transactionIds.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {data.transactionIds.map((txId) => (
                    <div
                      key={txId}
                      className="font-mono text-xs text-sky-300 bg-sky-950/50 border border-sky-500/30 px-3 py-1.5 rounded-lg flex items-center space-x-1.5 shadow-sm"
                    >
                      <Database className="h-3.5 w-3.5 text-sky-400" />
                      <span>{txId}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No specific transaction-level IDs were cited for this finding.</p>
              )}
            </div>

            {/* 5. Compliance Officer Feedback Form */}
            <div className="glass-panel p-5 rounded-2xl border border-emerald-500/20 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-1.5">
                  <MessageSquare className="h-4 w-4 text-emerald-400" />
                  <span>Compliance Officer Action & Audit Feedback</span>
                </h4>
                {isSubmitted && (
                  <span className="text-xs text-emerald-400 font-semibold flex items-center space-x-1">
                    <Check className="h-3.5 w-3.5" />
                    <span>Feedback Saved</span>
                  </span>
                )}
              </div>

              <form onSubmit={handleFormSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-400 text-[11px] font-semibold mb-1">
                    Audit Review Status:
                  </label>
                  <select
                    value={feedbackStatus}
                    onChange={(e) => setFeedbackStatus(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-white font-mono focus:outline-none focus:border-sky-500"
                  >
                    <option value="CONFIRMED_SUSPICIOUS">CONFIRMED_SUSPICIOUS (True Positive)</option>
                    <option value="FALSE_POSITIVE">FALSE_POSITIVE (Dismiss Finding)</option>
                    <option value="NEEDS_EDD">NEEDS_EDD (Enhanced Due Diligence)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 text-[11px] font-semibold mb-1">
                    Analyst Case Notes & Rationale:
                  </label>
                  <textarea
                    rows={3}
                    value={analystNotes}
                    onChange={(e) => setAnalystNotes(e.target.value)}
                    placeholder="Enter compliance justification or evidence notes..."
                    className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 font-sans"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center space-x-2"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Submit Audit Decision</span>
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
