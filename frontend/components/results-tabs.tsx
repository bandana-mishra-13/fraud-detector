"use client";

import { useEffect, useMemo, useState } from "react";
import { fmtCompact, fmtInt, fmtMoney } from "@/lib/format";
import type { AggregationRow, Flag, RiskLevel, RiskResult } from "@/lib/types";
import { BarList, ChartCard, ColumnChart } from "./charts";
import Pagination from "./pagination";

const FLAGS_PER_PAGE = 10;
const ROWS_PER_PAGE = 15;

const RISK_STYLES: Record<string, { badge: string; dot: string }> = {
  high: { badge: "border-red-200 bg-red-50 text-red-700", dot: "bg-red-500" },
  medium: { badge: "border-amber-200 bg-amber-50 text-amber-700", dot: "bg-amber-500" },
  low: { badge: "border-gray-200 bg-gray-50 text-gray-500", dot: "bg-gray-400" },
};

const ESCALATION_STYLES: Record<string, string> = {
  report: "border-red-200 text-red-600",
  review: "border-amber-300 text-amber-700",
  monitor: "border-gray-300 text-gray-500",
};

/** Which panels this run actually produced — drives which tabs exist. */
function availableTabs(result: RiskResult): string[] {
  const tabs: string[] = [];
  const isAggregation = Boolean(result.charts.aggregation_table);
  const hasDetection =
    result.flags.length > 0 ||
    result.plan.steps.some(
      (s) => s.tool === "risk_classification" && s.action === "invoked",
    );
  const hasCharts = Boolean(
    result.charts.txns_per_day ||
    result.charts.payment_formats ||
    result.charts.risk_breakdown ||
    result.charts.top_senders,
  );

  if (isAggregation) tabs.push("Results");
  if (hasDetection) tabs.push("Flags");
  if (hasCharts) tabs.push("Charts");
  tabs.push("Trace"); // always — the audit record
  return tabs;
}

function FlagRow({ flag }: { flag: Flag }) {
  const [open, setOpen] = useState(false);
  const risk = RISK_STYLES[flag.risk_level] ?? RISK_STYLES.low;

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-100 hover:bg-gray-50/60"
      >
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${risk.badge}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${risk.dot}`} />
          {flag.risk_level}
        </span>
        <span className="font-mono text-[12.5px] text-slate-800">{flag.entity_id}</span>
        <span className="rounded-md bg-indigo-50 px-1.5 py-0.5 text-[11px] font-medium text-indigo-600">
          {flag.pattern.replace(/_/g, " ")}
        </span>
        <span className="ml-auto text-[12px] tabular-nums text-gray-400">
          {flag.score.toFixed(2)}
        </span>
        <span className={`rounded-md border px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide ${ESCALATION_STYLES[flag.escalation]}`}>
          {flag.escalation}
        </span>
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          className={`shrink-0 text-gray-300 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div className="bg-gray-50/50 px-4 pb-3.5 pt-1">
          <p className="text-[13px] leading-relaxed text-slate-600">{flag.reason}</p>
          <dl className="mt-2.5 grid grid-cols-2 gap-x-6 gap-y-1.5 sm:grid-cols-3">
            {Object.entries(flag.evidence).map(([k, v]) => (
              <div key={k}>
                <dt className="text-[10.5px] uppercase tracking-wide text-gray-400">
                  {k.replace(/_/g, " ")}
                </dt>
                <dd className="text-[12.5px] font-medium tabular-nums text-slate-700">
                  {typeof v === "number" ? fmtInt(v) : String(v)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}

/** Risk + pattern filter bar. Counts are live, so zero-count options are
 * visibly unavailable rather than silently empty. */
function FilterBar({
  flags,
  risk,
  pattern,
  onRisk,
  onPattern,
}: {
  flags: Flag[];
  risk: RiskLevel | "all";
  pattern: string;
  onRisk: (r: RiskLevel | "all") => void;
  onPattern: (p: string) => void;
}) {
  const counts = useMemo(() => {
    const c: Record<string, number> = { high: 0, medium: 0, low: 0 };
    flags.forEach((f) => (c[f.risk_level] = (c[f.risk_level] ?? 0) + 1));
    return c;
  }, [flags]);

  const patterns = useMemo(
    () => Array.from(new Set(flags.map((f) => f.pattern))).sort(),
    [flags],
  );

  const levels: { id: RiskLevel | "all"; label: string; n: number; dot?: string }[] = [
    { id: "all", label: "All", n: flags.length },
    { id: "high", label: "High", n: counts.high, dot: "bg-red-500" },
    { id: "medium", label: "Medium", n: counts.medium, dot: "bg-amber-500" },
    { id: "low", label: "Low", n: counts.low, dot: "bg-gray-400" },
  ];

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-gray-100 px-3 py-2">
      <div className="inline-flex items-center gap-0.5 rounded-lg bg-gray-100/90 p-0.5">
        {levels.map((l) => {
          const active = risk === l.id;
          const empty = l.n === 0 && l.id !== "all";
          return (
            <button
              key={l.id}
              type="button"
              disabled={empty}
              onClick={() => onRisk(l.id)}
              className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11.5px] font-medium transition-[background-color,color,box-shadow] duration-150 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${active
                  ? "bg-white text-slate-900 shadow-[0_1px_2px_rgba(15,23,42,0.1)]"
                  : "text-gray-500 hover:text-slate-700"
                }`}
            >
              {l.dot && <span className={`h-1.5 w-1.5 rounded-full ${l.dot}`} />}
              {l.label}
              <span className="tabular-nums text-gray-400">{l.n}</span>
            </button>
          );
        })}
      </div>

      {patterns.length > 1 && (
        <select
          value={pattern}
          onChange={(e) => onPattern(e.target.value)}
          aria-label="Filter by AML pattern"
          className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-[11.5px] text-slate-600 focus:border-indigo-300 focus:outline-none"
        >
          <option value="all">All patterns</option>
          {patterns.map((p) => (
            <option key={p} value={p}>
              {p.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

function FlagsTab({ result }: { result: RiskResult }) {
  const [risk, setRisk] = useState<RiskLevel | "all">("all");
  const [pattern, setPattern] = useState("all");
  const [page, setPage] = useState(1);

  const filtered = useMemo(
    () =>
      result.flags.filter(
        (f) =>
          (risk === "all" || f.risk_level === risk) &&
          (pattern === "all" || f.pattern === pattern),
      ),
    [result.flags, risk, pattern],
  );

  useEffect(() => setPage(1), [risk, pattern]);

  const prior = result.charts.prior_flags;
  const entityAccounts = result.charts.entity_accounts;
  const pageCount = Math.max(1, Math.ceil(filtered.length / FLAGS_PER_PAGE));
  const start = (page - 1) * FLAGS_PER_PAGE;
  const shown = filtered.slice(start, start + FLAGS_PER_PAGE);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {entityAccounts && (
        <div className="border-b border-gray-100 px-4 py-3">
          <p className="text-[11px] uppercase tracking-wide text-gray-400">
            Entity resolved to {entityAccounts.length} account
            {entityAccounts.length === 1 ? "" : "s"}
          </p>
          <p className="mt-1 font-mono text-[12px] text-slate-600">
            {entityAccounts.join(" · ") || "no accounts found"}
          </p>
          {prior && prior.length > 0 && (
            <p className="mt-1.5 text-[12px] text-amber-700">
              {prior.length} prior audit flag{prior.length === 1 ? "" : "s"} on record
            </p>
          )}
        </div>
      )}

      {result.flags.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-14 text-center">
          <span aria-hidden="true" className="flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-50 text-emerald-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3 4.5 6v5c0 4.6 3.2 8 7.5 10 4.3-2 7.5-5.4 7.5-10V6L12 3Z" />
              <path d="m9.3 11.8 1.9 1.9 3.5-3.6" />
            </svg>
          </span>
          <p className="text-sm font-medium text-slate-700">No flags raised</p>
          <p className="max-w-sm text-[13px] leading-relaxed text-gray-400">
            Nothing in the analysed slice met the detection thresholds —
            behaviour looks consistent with normal activity.
          </p>
        </div>
      ) : (
        <>
          <FilterBar
            flags={result.flags}
            risk={risk}
            pattern={pattern}
            onRisk={setRisk}
            onPattern={setPattern}
          />
          <div className="min-h-0 flex-1 overflow-y-auto">
            {shown.length === 0 ? (
              <p className="px-6 py-10 text-center text-[13px] text-gray-400">
                No flags match this filter.
              </p>
            ) : (
              shown.map((f) => <FlagRow key={`${f.entity_id}-${f.pattern}`} flag={f} />)
            )}
          </div>
          <Pagination
            page={page}
            pageCount={pageCount}
            total={filtered.length}
            shownFrom={filtered.length === 0 ? 0 : start + 1}
            shownTo={Math.min(start + FLAGS_PER_PAGE, filtered.length)}
            onPage={setPage}
          />
        </>
      )}
    </div>
  );
}

function ResultsTable({ rows }: { rows: AggregationRow[] }) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter(
      (r) =>
        r.account.toLowerCase().includes(needle) ||
        r.customer.toLowerCase().includes(needle),
    );
  }, [rows, q]);

  useEffect(() => setPage(1), [q]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
  const start = (page - 1) * ROWS_PER_PAGE;
  const shown = filtered.slice(start, start + ROWS_PER_PAGE);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-gray-100 px-3 py-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by customer or account…"
          aria-label="Filter results"
          className="w-full max-w-xs rounded-lg border border-gray-200 bg-white px-2.5 py-1 text-[12px] text-slate-700 placeholder:text-gray-400 focus:border-indigo-300 focus:outline-none"
        />
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full text-[12.5px]">
          <thead className="sticky top-0 bg-white">
            <tr className="border-b border-gray-100 text-left text-[10.5px] uppercase tracking-wide text-gray-400">
              <th className="px-4 py-2.5 font-medium">Customer</th>
              <th className="px-4 py-2.5 font-medium">Account</th>
              <th className="px-4 py-2.5 text-right font-medium">Transactions</th>
              <th className="px-4 py-2.5 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.account} className="border-b border-gray-50 last:border-b-0 hover:bg-gray-50/60">
                <td className="px-4 py-2.5 text-slate-700">{r.customer}</td>
                <td className="px-4 py-2.5 font-mono text-slate-600">{r.account}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-slate-700">{fmtInt(r.txn_count)}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-slate-700">{fmtMoney(r.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {shown.length === 0 && (
          <p className="px-6 py-10 text-center text-[13px] text-gray-400">
            No rows match “{q}”.
          </p>
        )}
      </div>
      <Pagination
        page={page}
        pageCount={pageCount}
        total={filtered.length}
        shownFrom={filtered.length === 0 ? 0 : start + 1}
        shownTo={Math.min(start + ROWS_PER_PAGE, filtered.length)}
        onPage={setPage}
      />
    </div>
  );
}

function ChartsTab({ result }: { result: RiskResult }) {
  const c = result.charts;
  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-4">
      <div className="grid gap-4 lg:grid-cols-2">
      {c.txns_per_day && (
        <ChartCard title="Transactions per day">
          <ColumnChart
            ariaLabel="Transactions per day"
            data={c.txns_per_day.map((d) => ({ label: d.date.slice(5), value: d.count }))}
          />
        </ChartCard>
      )}
      {c.risk_breakdown && (
        <ChartCard title="Risk breakdown">
          <BarList
            ariaLabel="Flags by risk level"
            data={c.risk_breakdown.map((d) => ({
              label: d.level,
              value: d.count,
              color: d.level === "high" ? "bg-red-500" : d.level === "medium" ? "bg-amber-500" : "bg-gray-400",
              dot: d.level === "high" ? "bg-red-500" : d.level === "medium" ? "bg-amber-500" : "bg-gray-400",
            }))}
          />
        </ChartCard>
      )}
      {c.payment_formats && (
        <ChartCard title="Payment formats">
          <BarList
            ariaLabel="Transactions by payment format"
            data={c.payment_formats.map((d) => ({ label: d.format, value: d.count }))}
          />
        </ChartCard>
      )}
      {c.top_senders && (
        <ChartCard title="Top senders by volume">
          <BarList
            ariaLabel="Top sending accounts by volume"
            data={c.top_senders.slice(0, 6).map((d) => ({ label: d.account, value: d.volume }))}
          />
        </ChartCard>
      )}
      </div>
    </div>
  );
}

function TraceTab({ result }: { result: RiskResult }) {
  const trace = {
    run_id: result.run_id,
    plan: result.plan,
    kpis: result.kpis,
    llm_warning: result.llm_warning ?? null,
  };
  return (
    <pre className="max-h-[480px] overflow-auto p-4 font-mono text-[11.5px] leading-relaxed text-slate-600">
      {JSON.stringify(trace, null, 2)}
    </pre>
  );
}

export default function ResultsTabs({
  result,
  loading,
}: {
  result: RiskResult | null;
  loading?: boolean;
}) {
  // memoized: a fresh array each render would thrash the selection effect
  const tabs = useMemo(
    () => (result ? availableTabs(result) : ["Flags", "Charts", "Trace"]),
    [result],
  );
  const [selected, setSelected] = useState<string | null>(null);
  // never trust stale state — fall back to the first valid tab for this run
  const tab = selected && tabs.includes(selected) ? selected : tabs[0];

  // Badge reports what was FOUND, noting the display cap when one applies —
  // "50 flags" when 13,177 were raised is misleading.
  const aggRows = result?.charts.aggregation_table;
  const k = result?.kpis;
  let countLabel = "…";
  if (!loading && result) {
    if (aggRows) {
      const total = k?.aggregation_matches ?? aggRows.length;
      countLabel =
        total > aggRows.length
          ? `top ${aggRows.length} of ${fmtCompact(total)} matches`
          : `${fmtCompact(total)} matches`;
    } else {
      const total = k?.flags_raised ?? result.flags.length;
      countLabel =
        total > result.flags.length
          ? `top ${result.flags.length} of ${fmtCompact(total)} flags`
          : `${fmtCompact(total)} flags`;
    }
  }

  return (
    <section
      aria-label="Results"
      className="flex min-h-0 flex-1 flex-col rounded-xl border border-gray-200/80 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_8px_16px_-8px_rgba(15,23,42,0.04)]"
    >
      <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-3 py-2.5">
        <div role="tablist" aria-label="Result views" className="inline-flex items-center gap-0.5 rounded-lg bg-gray-100/90 p-0.5">
          {tabs.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={t === tab}
              onClick={() => setSelected(t)}
              className={`rounded-md px-3.5 py-1.5 text-[12.5px] font-medium transition-[background-color,color,box-shadow] duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${t === tab ? "bg-white text-slate-900 shadow-[0_1px_2px_rgba(15,23,42,0.08)]" : "text-gray-500 hover:text-slate-700"
                }`}
            >
              {t}
            </button>
          ))}
        </div>
        <span className="rounded-full border border-gray-200/80 bg-gray-50 px-2.5 py-0.5 text-[11px] font-medium text-gray-500">
          {countLabel}
        </span>
      </div>

      <div role="tabpanel" className="flex min-h-0 flex-1 flex-col">
        {loading ? (
          <SkeletonFlags />
        ) : !result ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-16 text-center">
            <span aria-hidden="true" className="flex h-11 w-11 items-center justify-center rounded-2xl border border-gray-200 bg-gray-50 text-gray-400">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3 4.5 6v5c0 4.6 3.2 8 7.5 10 4.3-2 7.5-5.4 7.5-10V6L12 3Z" />
                <path d="m9.3 11.8 1.9 1.9 3.5-3.6" />
              </svg>
            </span>
            <p className="text-sm font-medium text-slate-700">No analysis yet</p>
            <p className="max-w-sm text-[13px] leading-relaxed text-gray-400">
              Run a query — flagged entities, risk levels, explanations and
              escalation calls land here.
            </p>
          </div>
        ) : tab === "Results" && aggRows ? (
          <ResultsTable rows={aggRows} />
        ) : tab === "Flags" ? (
          <FlagsTab result={result} />
        ) : tab === "Charts" ? (
          <ChartsTab result={result} />
        ) : (
          <TraceTab result={result} />
        )}
      </div>
    </section>
  );
}

function SkeletonFlags() {
  return (
    <div aria-label="Loading results" className="p-1">
      {[0.9, 0.7, 0.5, 0.35, 0.22].map((op, i) => (
        <div
          key={i}
          className="flex items-center gap-3 border-b border-gray-50 px-3 py-3 last:border-b-0"
          style={{ opacity: op }}
        >
          <span className="skeleton h-5 w-16 rounded-full" />
          <span className="skeleton h-3 w-24 rounded" />
          <span className="skeleton h-4 w-20 rounded-md" />
          <span className="skeleton ml-auto h-3 w-8 rounded" />
          <span className="skeleton h-5 w-14 rounded-md" />
        </div>
      ))}
    </div>
  );
}
