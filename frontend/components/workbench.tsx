"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, postQuery, type ToolOverrides } from "@/lib/api";
import { useSessions } from "@/lib/use-sessions";
import AgentRail, { type AgentRailHandle } from "./agent-rail";
import KpiStrip from "./kpi-strip";
import ResultsTabs from "./results-tabs";
import SummaryCard from "./summary-card";

const EXAMPLES = [
  "Analyse this dataset for suspicious activity",
  "Find structuring patterns in the last 30 days",
  "Which customers made 10+ transactions under $10,000?",
  "Is customer 4521 suspicious?",
];

export default function Workbench() {
  const {
    sessions,
    activeSession,
    activeSessionId,
    activeRun,
    activeRunId,
    startNewSession,
    addRun,
    selectRun,
    deleteRun,
    deleteSession,
  } = useSessions();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<ToolOverrides>({});
  const railRef = useRef<AgentRailHandle>(null);

  const submit = async (query: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await postQuery(query, overrides);
      addRun(query, result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Unexpected error — see console.");
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // keyboard shortcuts: ⌘/Ctrl+K or "/" focuses composer; 1–4 fill a demo query
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing = el && (el.tagName === "TEXTAREA" || el.tagName === "INPUT");
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        railRef.current?.focusComposer();
        return;
      }
      if (typing) return;
      if (e.key === "/") {
        e.preventDefault();
        railRef.current?.focusComposer();
      } else if (["1", "2", "3", "4"].includes(e.key)) {
        railRef.current?.setQuery(EXAMPLES[Number(e.key) - 1]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const showResults = loading || activeRun;

  return (
    <div className="grid flex-1 lg:min-h-0 lg:grid-cols-[340px_1fr]">
      <AgentRail
        ref={railRef}
        sessions={sessions}
        activeSessionId={activeSessionId}
        activeRun={activeRun}
        activeRunId={activeRunId}
        loading={loading}
        error={error}
        overrides={overrides}
        onOverridesChange={setOverrides}
        onSubmit={submit}
        onNewSession={startNewSession}
        onSelectRun={selectRun}
        onDeleteRun={deleteRun}
        onDeleteSession={deleteSession}
      />

      <main className="flex flex-col gap-4 px-4 py-4 sm:px-5 lg:min-h-0 lg:overflow-y-auto">
        {showResults ? (
          <>
            <KpiStrip kpis={activeRun?.result.kpis ?? null} loading={loading} />
            {!loading && activeRun && <SummaryCard result={activeRun.result} />}
            {/* key: remount per run so filters + pagination reset cleanly */}
            <ResultsTabs
              key={activeRun?.id ?? "loading"}
              result={activeRun?.result ?? null}
              loading={loading}
            />
          </>
        ) : (
          <ColdStart
            sessionEmpty={(activeSession?.runs.length ?? 0) === 0}
            onPick={(q) => railRef.current?.setQuery(q)}
          />
        )}
      </main>
    </div>
  );
}

/** First-run focal state — the recommendations live here, centered. */
function ColdStart({
  onPick,
  sessionEmpty,
}: {
  onPick: (q: string) => void;
  sessionEmpty: boolean;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
      <span
        aria-hidden="true"
        className="fade-up flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-100 bg-indigo-50 text-indigo-600"
      >
        <svg width="26" height="26" viewBox="0 0 64 64" fill="none" aria-hidden="true">
          <ellipse cx="32" cy="32" rx="19" ry="11.5" fill="none" stroke="currentColor" strokeWidth="3.5" />
          <circle cx="32" cy="32" r="5.5" fill="currentColor" />
        </svg>
      </span>
      <h2 className="fade-up mt-4 text-lg font-semibold tracking-tight text-slate-900" style={{ animationDelay: "40ms" }}>
        {sessionEmpty ? "Ask Argus about the transactions" : "New session — ask away"}
      </h2>
      <p className="fade-up mt-1.5 max-w-md text-[13.5px] leading-relaxed text-gray-500" style={{ animationDelay: "80ms" }}>
        Type a question in the panel, or start with an example. The agent plans
        which tools to run, then returns explainable, risk-ranked flags.
      </p>
      <div className="fade-up mt-5 flex max-w-lg flex-col items-stretch gap-2 sm:min-w-[420px]" style={{ animationDelay: "120ms" }}>
        {EXAMPLES.map((q, i) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="group flex items-center gap-2.5 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-left text-[13px] text-slate-600 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-colors duration-150 hover:border-indigo-200 hover:bg-indigo-50/50 hover:text-indigo-700"
          >
            <kbd className="shrink-0 rounded border border-gray-200 bg-gray-50 px-1.5 text-[10.5px] text-gray-400 group-hover:border-indigo-200 group-hover:text-indigo-500">
              {i + 1}
            </kbd>
            <span>{q}</span>
          </button>
        ))}
      </div>
      <p className="fade-up mt-6 text-[11.5px] text-gray-400" style={{ animationDelay: "160ms" }}>
        Press <kbd className="rounded border border-gray-200 bg-white px-1 text-[10px]">/</kbd> to focus ·{" "}
        <kbd className="rounded border border-gray-200 bg-white px-1 text-[10px]">1</kbd>–
        <kbd className="rounded border border-gray-200 bg-white px-1 text-[10px]">4</kbd> for examples
      </p>
    </div>
  );
}
