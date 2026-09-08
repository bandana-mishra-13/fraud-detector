"use client";

import { forwardRef, useImperativeHandle, useRef, useState } from "react";
import type { ToolOverrides } from "@/lib/api";
import { fmtMs } from "@/lib/format";
import type { PlanStep, Session, SessionRun } from "@/lib/types";
import SessionHistory from "./session-history";
import ToolPicker from "./tool-picker";

const GHOST_STEPS = [
  { title: "Parse intent", detail: "filters, entities, AML pattern" },
  { title: "Plan tools", detail: "only what the question needs" },
  { title: "Run analysis", detail: "rules + anomaly models" },
  { title: "Explain & escalate", detail: "monitor / review / report" },
];

/** Human labels for the filters the parser extracts, shown as chips. */
function filterChips(filters: Record<string, unknown>): string[] {
  const out: string[] = [];
  const f = filters;
  if (f.last_n_days) out.push(`last ${f.last_n_days} days`);
  if (f.date_from) out.push(`from ${f.date_from}`);
  if (f.date_to) out.push(`to ${f.date_to}`);
  if (f.max_amount) out.push(`≤ $${Number(f.max_amount).toLocaleString()}`);
  if (f.min_amount) out.push(`≥ $${Number(f.min_amount).toLocaleString()}`);
  if (f.min_txn_count) out.push(`${f.min_txn_count}+ txns`);
  if (f.currency) out.push(String(f.currency));
  if (f.payment_format) out.push(String(f.payment_format));
  if (f.bank) out.push(`bank ${f.bank}`);
  if (f.account) out.push(`acct ${f.account}`);
  if (f.customer) out.push(`customer ${f.customer}`);
  return out;
}

function isForced(step: PlanStep): boolean {
  return /reviewer/i.test(step.reason);
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-gray-400">
      {children}
    </p>
  );
}

export type AgentRailHandle = { focusComposer: () => void; setQuery: (q: string) => void };

type Props = {
  sessions: Session[];
  activeSessionId: string;
  activeRun: SessionRun | null;
  activeRunId: string | null;
  loading: boolean;
  error: string | null;
  overrides: ToolOverrides;
  onOverridesChange: (o: ToolOverrides) => void;
  onSubmit: (query: string) => void;
  onNewSession: () => void;
  onSelectRun: (sessionId: string, runId: string) => void;
  onDeleteRun: (sessionId: string, runId: string) => void;
  onDeleteSession: (sessionId: string) => void;
};

const AgentRail = forwardRef<AgentRailHandle, Props>(function AgentRail(
  {
    sessions,
    activeSessionId,
    activeRun,
    loading,
    error,
    overrides,
    onOverridesChange,
    onSubmit,
    onNewSession,
    onSelectRun,
    onDeleteRun,
    onDeleteSession,
  },
  ref,
) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const active = activeRun;

  useImperativeHandle(ref, () => ({
    focusComposer: () => inputRef.current?.focus(),
    setQuery: (q: string) => {
      setQuery(q);
      inputRef.current?.focus();
    },
  }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q || loading) return;
    onSubmit(q);
  };

  return (
    <aside
      aria-label="Agent"
      className="flex flex-col gap-7 border-b border-gray-200/80 bg-[#FBFBFC] px-4 py-5 lg:h-full lg:overflow-y-auto lg:border-b-0 lg:border-r"
    >
      {/* composer */}
      <section>
        <SectionLabel>New analysis</SectionLabel>
        <form
          onSubmit={submit}
          className="mt-2.5 rounded-xl border border-gray-200/90 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_8px_16px_-8px_rgba(15,23,42,0.04)] transition-[border-color,box-shadow] duration-150 focus-within:border-indigo-300 focus-within:shadow-[0_0_0_4px_rgba(79,70,229,0.07)]"
        >
          <textarea
            ref={inputRef}
            value={query}
            rows={3}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Ask Argus anything about the transaction data…"
            aria-label="Ask Argus a question about the transaction data"
            autoFocus
            className="w-full resize-none bg-transparent px-3.5 pb-1 pt-3 text-[13.5px] leading-snug text-slate-900 placeholder:text-gray-400 focus:outline-none"
          />
          <div className="flex items-center justify-between gap-2 px-2 pb-2">
            <ToolPicker overrides={overrides} onChange={onOverridesChange} disabled={loading} />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 text-[12.5px] font-medium text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.16)] transition-[background-color,transform,opacity] duration-150 hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <>
                  <svg className="animate-spin" width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.3" strokeWidth="3" />
                    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                  Analysing…
                </>
              ) : (
                <>
                  Analyse
                  <kbd className="rounded bg-white/15 px-1 font-sans text-[10px] leading-4">↵</kbd>
                </>
              )}
            </button>
          </div>
        </form>

        {error && (
          <p
            role="alert"
            className="mt-2.5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] leading-snug text-red-700"
          >
            {error}
          </p>
        )}
      </section>

      <SessionHistory
        sessions={sessions}
        activeSessionId={activeSessionId}
        activeRunId={active?.id ?? null}
        onNewSession={onNewSession}
        onSelectRun={onSelectRun}
        onDeleteRun={onDeleteRun}
        onDeleteSession={onDeleteSession}
      />

      {/* execution plan */}
      <section className="flex-1">
        <div className="flex items-center justify-between">
          <SectionLabel>Execution plan</SectionLabel>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10.5px] font-medium ${
              loading
                ? "border-indigo-200 bg-indigo-50 text-indigo-600"
                : active
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-gray-200/80 bg-white text-gray-400"
            }`}
          >
            <span
              className={`h-1 w-1 rounded-full ${
                loading ? "animate-pulse bg-indigo-500" : active ? "bg-emerald-500" : "bg-gray-300"
              }`}
            />
            {loading ? "Planning" : active ? active.result.plan.intent : "Idle"}
          </span>
        </div>

        {/* filter chips (real run only) */}
        {!loading && active && filterChips(active.result.plan.filters).length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {filterChips(active.result.plan.filters).map((c) => (
              <span
                key={c}
                className="rounded-md border border-indigo-100 bg-indigo-50/60 px-1.5 py-0.5 text-[10.5px] font-medium text-indigo-600"
              >
                {c}
              </span>
            ))}
          </div>
        )}

        {loading ? (
          <ol className="mt-3.5 space-y-3" aria-label="Planning">
            {[0, 1, 2, 3, 4].map((i) => (
              <li key={i} className="flex items-center gap-3" style={{ opacity: 1 - i * 0.16 }}>
                <span className="skeleton h-6 w-6 shrink-0 rounded-full" />
                <span className="flex-1 space-y-1.5">
                  <span className="skeleton block h-2.5 w-24 rounded" />
                  <span className="skeleton block h-2 w-36 rounded" />
                </span>
              </li>
            ))}
          </ol>
        ) : active ? (
          <ol className="relative mt-3.5 space-y-3">
            <span
              aria-hidden="true"
              className="absolute bottom-3 left-[11px] top-3 w-px bg-gradient-to-b from-transparent via-gray-200 to-transparent"
            />
            {active.result.plan.steps.map((step) => {
              const invoked = step.action === "invoked";
              const forced = isForced(step);
              return (
                <li key={step.tool} className="relative flex gap-3">
                  <span
                    className={`z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] ${
                      invoked
                        ? forced
                          ? "border-emerald-200 bg-emerald-50 text-emerald-600"
                          : "border-indigo-200 bg-indigo-50 text-indigo-600"
                        : "border-dashed border-gray-300 bg-[#FBFBFC] text-gray-400"
                    }`}
                  >
                    {invoked ? (
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="m5 13 4 4L19 7" />
                      </svg>
                    ) : (
                      "–"
                    )}
                  </span>
                  <div className="min-w-0 pt-0.5">
                    <p className="flex items-baseline gap-2 text-[12.5px] font-medium leading-tight">
                      <span className={invoked ? "text-slate-700" : "text-gray-400"}>
                        {step.tool}
                      </span>
                      {invoked && step.duration_ms !== null && (
                        <span className="text-[10.5px] font-normal tabular-nums text-gray-400">
                          {fmtMs(step.duration_ms)}
                        </span>
                      )}
                      {forced && (
                        <span className="rounded bg-emerald-50 px-1 text-[9.5px] font-semibold uppercase tracking-wide text-emerald-600">
                          you
                        </span>
                      )}
                      {!invoked && !forced && (
                        <span className="text-[10.5px] font-normal text-gray-400">skipped</span>
                      )}
                    </p>
                    <p className="mt-0.5 text-[11.5px] leading-snug text-gray-400/90">
                      {step.reason}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        ) : (
          <>
            <ol className="relative mt-3.5 space-y-4">
              <span
                aria-hidden="true"
                className="absolute bottom-3 left-[11px] top-3 w-px bg-gradient-to-b from-transparent via-gray-200 to-transparent"
              />
              {GHOST_STEPS.map((step, i) => (
                <li key={step.title} className="relative flex gap-3">
                  <span className="z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-dashed border-gray-300 bg-[#FBFBFC] text-[11px] font-medium text-gray-400">
                    {i + 1}
                  </span>
                  <div className="pt-0.5">
                    <p className="text-[12.5px] font-medium leading-tight text-gray-400">{step.title}</p>
                    <p className="mt-0.5 text-[11.5px] leading-snug text-gray-400/70">{step.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-[11.5px] leading-snug text-gray-400">
              The real plan — tools invoked, tools skipped, and why — replaces
              this when a query runs.
            </p>
          </>
        )}
      </section>
    </aside>
  );
});

export default AgentRail;
