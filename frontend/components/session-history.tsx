"use client";

import { useState } from "react";
import { fmtMs } from "@/lib/format";
import type { Session } from "@/lib/types";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-gray-400">
      {children}
    </p>
  );
}

function TrashIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
    </svg>
  );
}

export default function SessionHistory({
  sessions,
  activeSessionId,
  activeRunId,
  onNewSession,
  onSelectRun,
  onDeleteRun,
  onDeleteSession,
}: {
  sessions: Session[];
  activeSessionId: string;
  activeRunId: string | null;
  onNewSession: () => void;
  onSelectRun: (sessionId: string, runId: string) => void;
  onDeleteRun: (sessionId: string, runId: string) => void;
  onDeleteSession: (sessionId: string) => void;
}) {
  // collapsed state per session; active session starts expanded
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const isCollapsed = (id: string) =>
    id in collapsed ? collapsed[id] : id !== activeSessionId;

  return (
    <section>
      <div className="flex items-center justify-between">
        <SectionLabel>Sessions</SectionLabel>
        <button
          type="button"
          onClick={onNewSession}
          className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-1.5 py-0.5 text-[11px] font-medium text-indigo-600 transition-colors duration-150 hover:border-indigo-200 hover:bg-indigo-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
            <path d="M12 5v14M5 12h14" />
          </svg>
          New session
        </button>
      </div>

      <div className="mt-2.5 space-y-1.5">
        {sessions.map((session) => {
          const collapsedNow = isCollapsed(session.id);
          const isActiveSession = session.id === activeSessionId;
          return (
            <div
              key={session.id}
              className={`overflow-hidden rounded-lg border ${
                isActiveSession ? "border-indigo-200/80" : "border-gray-200/70"
              }`}
            >
              <div
                className={`group/session flex w-full items-center gap-2 px-2.5 py-2 transition-colors duration-150 ${
                  isActiveSession ? "bg-indigo-50/50" : "bg-white hover:bg-gray-50"
                }`}
              >
                <button
                  type="button"
                  onClick={() =>
                    setCollapsed((c) => ({ ...c, [session.id]: !collapsedNow }))
                  }
                  aria-expanded={!collapsedNow}
                  className="flex min-w-0 flex-1 items-center gap-2 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                >
                  <svg
                    width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
                    className={`shrink-0 text-gray-400 transition-transform duration-150 ${collapsedNow ? "" : "rotate-90"}`}
                    aria-hidden="true"
                  >
                    <path d="m9 6 6 6-6 6" />
                  </svg>
                  <span className={`min-w-0 flex-1 truncate text-[12.5px] font-medium ${isActiveSession ? "text-indigo-900" : "text-slate-700"}`}>
                    {session.name}
                  </span>
                </button>
                {isActiveSession && (
                  <span className="shrink-0 rounded-full bg-indigo-100 px-1.5 py-0.5 text-[9.5px] font-semibold uppercase tracking-wide text-indigo-600">
                    active
                  </span>
                )}
                <span className="shrink-0 text-[11px] tabular-nums text-gray-400">
                  {session.runs.length}
                </span>
                <button
                  type="button"
                  aria-label={`Delete ${session.name}`}
                  title="Delete session"
                  onClick={() => onDeleteSession(session.id)}
                  className="shrink-0 rounded p-0.5 text-gray-300 opacity-0 transition-[opacity,color] duration-150 hover:text-red-500 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 group-hover/session:opacity-100"
                >
                  <TrashIcon />
                </button>
              </div>

              {!collapsedNow && (
                <div className="border-t border-gray-100 bg-white p-1">
                  {session.runs.length === 0 ? (
                    <p className="px-2 py-1.5 text-[11.5px] text-gray-400">
                      No runs yet in this session.
                    </p>
                  ) : (
                    session.runs.map((run) => {
                      const isActive = run.id === activeRunId;
                      return (
                        <div
                          key={run.id}
                          className={`group/run flex items-start gap-1 rounded-md transition-colors duration-150 ${
                            isActive ? "bg-indigo-50" : "hover:bg-gray-50"
                          }`}
                        >
                          <button
                            type="button"
                            onClick={() => onSelectRun(session.id, run.id)}
                            className="min-w-0 flex-1 px-2.5 py-1.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                          >
                            <p className={`truncate text-[12px] ${isActive ? "font-medium text-indigo-900" : "text-slate-600"}`}>
                              {run.query}
                            </p>
                            <p className="mt-0.5 flex items-center gap-2 text-[10.5px] text-gray-400">
                              <span className="font-medium text-indigo-500/80">{run.result.plan.intent}</span>
                              <span>{run.result.kpis.flags_raised} flags</span>
                              <span>{fmtMs(run.result.kpis.elapsed_ms)}</span>
                            </p>
                          </button>
                          <button
                            type="button"
                            aria-label="Delete this run"
                            title="Delete run"
                            onClick={() => onDeleteRun(session.id, run.id)}
                            className="mt-1.5 mr-1 shrink-0 rounded p-0.5 text-gray-300 opacity-0 transition-[opacity,color] duration-150 hover:text-red-500 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 group-hover/run:opacity-100"
                          >
                            <TrashIcon />
                          </button>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
