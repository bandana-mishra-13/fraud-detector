"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
  ExternalLink,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { Flag, RiskTier, submitAnalystFeedback } from "@/lib/api";

interface ResultsTableProps {
  flags: Flag[];
  queryId?: string;
  onSelectFlag?: (flag: Flag) => void;
}

export const ResultsTable: React.FC<ResultsTableProps> = ({ flags, queryId, onSelectFlag }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [sortField, setSortField] = useState<"severity" | "timestamp" | "entity_id" | "typology">("severity");
  const [sortAsc, setSortAsc] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 6;

  // Local state for feedback modifications
  const [feedbackState, setFeedbackState] = useState<Record<string, { status: string; notes: string }>>({});
  const [selectedFlagForModal, setSelectedFlagForModal] = useState<Flag | null>(null);
  const [feedbackNote, setFeedbackNote] = useState("");
  const [submittingFlagId, setSubmittingFlagId] = useState<string | null>(null);

  const getSeverityWeight = (s: RiskTier | string): number => {
    switch (String(s).toUpperCase()) {
      case "CRITICAL":
        return 4;
      case "HIGH":
        return 3;
      case "MEDIUM":
        return 2;
      case "LOW":
        return 1;
      default:
        return 0;
    }
  };

  const getSeverityBadge = (s: RiskTier | string) => {
    const sev = String(s).toUpperCase();
    switch (sev) {
      case "CRITICAL":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 shadow-sm shadow-rose-500/20">
            <ShieldAlert className="h-3 w-3" />
            <span>CRITICAL</span>
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
            <AlertTriangle className="h-3 w-3" />
            <span>HIGH</span>
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
            <Info className="h-3 w-3" />
            <span>MEDIUM</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            <ShieldCheck className="h-3 w-3" />
            <span>LOW</span>
          </span>
        );
    }
  };

  const getFeedbackBadge = (status?: string) => {
    const s = (status || "PENDING").toUpperCase();
    switch (s) {
      case "CONFIRMED_SUSPICIOUS":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-rose-950/60 text-rose-300 border border-rose-500/40">
            <CheckCircle2 className="h-3 w-3 text-rose-400" />
            <span>Confirmed Suspicious</span>
          </span>
        );
      case "FALSE_POSITIVE":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-600">
            <XCircle className="h-3 w-3 text-slate-400" />
            <span>False Positive</span>
          </span>
        );
      case "UNDER_REVIEW":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-amber-950/60 text-amber-300 border border-amber-500/40">
            <Clock className="h-3 w-3 text-amber-400" />
            <span>Under Review</span>
          </span>
        );
      case "DISMISSED":
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-900 text-slate-400 border border-white/10">
            <span>Dismissed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-sky-950/40 text-sky-400 border border-sky-500/30">
            <span>Pending Review</span>
          </span>
        );
    }
  };

  // Filter and sort flags
  const filteredFlags = flags.filter((f) => {
    const currentStatus = feedbackState[f.flag_id]?.status || f.feedback_status || "PENDING";
    const matchesSearch =
      searchTerm === "" ||
      (f.entity_id && f.entity_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      f.rule_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (f.typology && f.typology.toLowerCase().includes(searchTerm.toLowerCase())) ||
      f.reason.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesSeverity = severityFilter === "ALL" || f.severity.toUpperCase() === severityFilter;
    const matchesStatus = statusFilter === "ALL" || currentStatus.toUpperCase() === statusFilter;

    return matchesSearch && matchesSeverity && matchesStatus;
  });

  const sortedFlags = [...filteredFlags].sort((a, b) => {
    let comp = 0;
    if (sortField === "severity") {
      comp = getSeverityWeight(a.severity) - getSeverityWeight(b.severity);
    } else if (sortField === "entity_id") {
      comp = (a.entity_id || "").localeCompare(b.entity_id || "");
    } else if (sortField === "typology") {
      comp = (a.typology || "").localeCompare(b.typology || "");
    } else {
      comp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    }
    return sortAsc ? comp : -comp;
  });

  const totalPages = Math.max(1, Math.ceil(sortedFlags.length / itemsPerPage));
  const paginatedFlags = sortedFlags.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const handleApplyFeedback = async (flagId: string, status: string, notes: string) => {
    setSubmittingFlagId(flagId);
    try {
      await submitAnalystFeedback({
        flagId,
        feedbackStatus: status,
        notes,
        queryId,
      });

      setFeedbackState((prev) => ({
        ...prev,
        [flagId]: { status, notes },
      }));
      setSelectedFlagForModal(null);
      setFeedbackNote("");
    } catch (err) {
      console.error("Feedback submit error:", err);
    } finally {
      setSubmittingFlagId(null);
    }
  };

  if (!flags || flags.length === 0) {
    return (
      <div className="glass-panel p-8 rounded-2xl text-center space-y-3">
        <ShieldCheck className="h-10 w-10 text-emerald-400 mx-auto" />
        <h3 className="text-sm font-semibold text-slate-200">No AML Red Flags Detected</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          The executed deterministic tools and filters evaluated this query with zero anomalous rule breaches.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header & Controls Toolbar */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
              <span>Flagged AML Findings</span>
              <span className="px-2 py-0.2 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/30 text-xs font-mono">
                {flags.length} total
              </span>
            </h3>
            <p className="text-[11px] text-slate-400">Deterministic rule violations and typology detections</p>
          </div>
        </div>

        {/* Filter / Search Bar */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search account, rule..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-900/80 border border-white/10 text-slate-200 pl-8 pr-3 py-1.5 rounded-xl text-xs focus:outline-none focus:border-sky-500"
            />
          </div>

          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-slate-900/80 border border-white/10 text-slate-200 px-3 py-1.5 rounded-xl text-xs focus:outline-none focus:border-sky-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-slate-900/80 border border-white/10 text-slate-200 px-3 py-1.5 rounded-xl text-xs focus:outline-none focus:border-sky-500"
          >
            <option value="ALL">All Review Statuses</option>
            <option value="PENDING">Pending Review</option>
            <option value="CONFIRMED_SUSPICIOUS">Confirmed Suspicious</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="FALSE_POSITIVE">False Positive</option>
          </select>
        </div>
      </div>

      {/* Main Table */}
      <div className="glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 border-b border-white/10 text-slate-400 uppercase tracking-wider font-semibold text-[10px]">
              <tr>
                <th
                  onClick={() => {
                    if (sortField === "severity") setSortAsc(!sortAsc);
                    else {
                      setSortField("severity");
                      setSortAsc(false);
                    }
                  }}
                  className="py-3 px-4 cursor-pointer hover:text-sky-400 transition-colors"
                >
                  <div className="flex items-center space-x-1">
                    <span>Severity</span>
                    {sortField === "severity" && (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                  </div>
                </th>
                <th
                  onClick={() => {
                    if (sortField === "typology") setSortAsc(!sortAsc);
                    else {
                      setSortField("typology");
                      setSortAsc(true);
                    }
                  }}
                  className="py-3 px-4 cursor-pointer hover:text-sky-400 transition-colors"
                >
                  <div className="flex items-center space-x-1">
                    <span>Typology / Rule</span>
                    {sortField === "typology" && (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                  </div>
                </th>
                <th
                  onClick={() => {
                    if (sortField === "entity_id") setSortAsc(!sortAsc);
                    else {
                      setSortField("entity_id");
                      setSortAsc(true);
                    }
                  }}
                  className="py-3 px-4 cursor-pointer hover:text-sky-400 transition-colors"
                >
                  <div className="flex items-center space-x-1">
                    <span>Account / Entity</span>
                    {sortField === "entity_id" && (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                  </div>
                </th>
                <th className="py-3 px-4">Cited Evidence</th>
                <th className="py-3 px-4">Compliance Review</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {paginatedFlags.map((flag) => {
                const currentFeedback = feedbackState[flag.flag_id] || {
                  status: flag.feedback_status || "PENDING",
                  notes: flag.analyst_notes || "",
                };

                return (
                  <tr
                    key={flag.flag_id}
                    className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                    onClick={() => onSelectFlag && onSelectFlag(flag)}
                  >
                    <td className="py-3.5 px-4 whitespace-nowrap">{getSeverityBadge(flag.severity)}</td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-200">{flag.typology || "AML Violation"}</div>
                      <div className="text-[11px] text-slate-400 line-clamp-1">{flag.rule_name}</div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="font-mono text-sky-400 bg-sky-950/40 px-2 py-0.5 rounded border border-sky-500/20 font-medium">
                        {flag.entity_id || "Multiple Accounts"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 max-w-xs">
                      <p className="text-[11px] text-slate-300 line-clamp-2 leading-relaxed">{flag.reason}</p>
                      {flag.transaction_ids && flag.transaction_ids.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {flag.transaction_ids.slice(0, 3).map((tx) => (
                            <span
                              key={tx}
                              className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-900 border border-white/10 text-slate-400"
                            >
                              {tx}
                            </span>
                          ))}
                          {flag.transaction_ids.length > 3 && (
                            <span className="text-[9px] text-slate-500">+{flag.transaction_ids.length - 3} more</span>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">{getFeedbackBadge(currentFeedback.status)}</td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedFlagForModal(flag);
                          setFeedbackNote(currentFeedback.notes || "");
                        }}
                        className="px-2.5 py-1 rounded-lg border border-sky-500/30 hover:bg-sky-500/10 text-sky-400 text-xs transition-colors inline-flex items-center space-x-1"
                      >
                        <MessageSquare className="h-3 w-3" />
                        <span>Review</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="p-3 bg-slate-900/80 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
          <span>
            Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, sortedFlags.length)} of{" "}
            {sortedFlags.length} findings
          </span>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-2.5 py-1 rounded-lg border border-white/10 hover:bg-slate-800 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="font-mono text-slate-300">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-2.5 py-1 rounded-lg border border-white/10 hover:bg-slate-800 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Analyst Feedback Modal */}
      {selectedFlagForModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel p-6 rounded-2xl max-w-lg w-full border border-sky-500/30 space-y-4 shadow-2xl animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="h-5 w-5 text-sky-400" />
                <h4 className="text-sm font-semibold text-white">Compliance Case Review</h4>
              </div>
              <button
                onClick={() => setSelectedFlagForModal(null)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Flag ID</span>
                <span className="font-mono text-slate-200">{selectedFlagForModal.flag_id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Entity</span>
                <span className="font-mono text-sky-400">{selectedFlagForModal.entity_id || "N/A"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Typology</span>
                <span className="text-slate-200 font-semibold">{selectedFlagForModal.typology}</span>
              </div>
              <p className="text-[11px] text-slate-300 bg-slate-900/60 p-2.5 rounded-xl border border-white/5">
                {selectedFlagForModal.reason}
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Investigative Notes / SAR Rationale:</label>
              <textarea
                rows={3}
                value={feedbackNote}
                onChange={(e) => setFeedbackNote(e.target.value)}
                placeholder="Enter case determination notes, SAR reference, or false-positive rationale..."
                className="w-full bg-slate-950 border border-white/10 text-slate-100 p-2.5 rounded-xl text-xs focus:outline-none focus:border-sky-500 font-sans"
              />
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
              <button
                type="button"
                disabled={submittingFlagId === selectedFlagForModal.flag_id}
                onClick={() => handleApplyFeedback(selectedFlagForModal.flag_id, "CONFIRMED_SUSPICIOUS", feedbackNote)}
                className="px-3 py-2 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 text-[11px] font-semibold transition-all"
              >
                Confirm SAR
              </button>
              <button
                type="button"
                disabled={submittingFlagId === selectedFlagForModal.flag_id}
                onClick={() => handleApplyFeedback(selectedFlagForModal.flag_id, "UNDER_REVIEW", feedbackNote)}
                className="px-3 py-2 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 text-[11px] font-semibold transition-all"
              >
                Hold / Review
              </button>
              <button
                type="button"
                disabled={submittingFlagId === selectedFlagForModal.flag_id}
                onClick={() => handleApplyFeedback(selectedFlagForModal.flag_id, "FALSE_POSITIVE", feedbackNote)}
                className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 text-[11px] font-semibold transition-all"
              >
                False Positive
              </button>
              <button
                type="button"
                disabled={submittingFlagId === selectedFlagForModal.flag_id}
                onClick={() => handleApplyFeedback(selectedFlagForModal.flag_id, "DISMISSED", feedbackNote)}
                className="px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 border border-white/10 text-[11px] font-semibold transition-all"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
