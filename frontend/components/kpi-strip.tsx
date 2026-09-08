/**
 * KPI row of stat tiles.
 * Tile contract: sentence-case label (no trailing colon), semibold value in
 * proportional figures. Em-dash placeholders until a run completes.
 */
import { fmtCompact, fmtMs } from "@/lib/format";
import type { Kpis } from "@/lib/types";

const ICONS: Record<string, React.ReactNode> = {
  scanned: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
      <ellipse cx="12" cy="6" rx="7" ry="2.5" />
      <path d="M5 6v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6" />
      <path d="M5 12v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-6" />
    </svg>
  ),
  flags: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 21V4.5C8.5 2.7 11.5 6 17 4.2V14c-5.5 1.8-8.5-1.5-12 .3" />
    </svg>
  ),
  high: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m12 4.5 8.5 15h-17l8.5-15Z" />
      <path d="M12 10.5v3.5M12 17h.01" />
    </svg>
  ),
  time: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l2.5 2.5" />
    </svg>
  ),
};

export default function KpiStrip({
  kpis,
  loading,
}: {
  kpis: Kpis | null;
  loading?: boolean;
}) {
  // An aggregation query answers a counting question — flag/risk tiles would
  // read as "0 flags" and look like a failure. Show what it actually produced.
  const isAggregation = kpis?.aggregation_matches !== undefined;

  const tiles = [
    {
      label: "Transactions scanned",
      icon: ICONS.scanned,
      value: kpis ? fmtCompact(kpis.transactions_scanned) : null,
    },
    isAggregation
      ? {
          label: "Matching customers",
          icon: ICONS.flags,
          value: kpis ? fmtCompact(kpis.aggregation_matches ?? 0) : null,
        }
      : {
          label: "Flags raised",
          icon: ICONS.flags,
          value: kpis ? String(kpis.flags_raised) : null,
        },
    isAggregation
      ? {
          label: "Threshold rule",
          icon: ICONS.high,
          value: kpis ? "applied" : null,
        }
      : {
          label: "High risk",
          icon: ICONS.high,
          value: kpis ? String(kpis.high_risk) : null,
          alert: kpis ? kpis.high_risk > 0 : false,
        },
    {
      label: "Analysis time",
      icon: ICONS.time,
      value: kpis ? fmtMs(kpis.elapsed_ms) : null,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {tiles.map((t) => (
        <div
          key={t.label}
          className="rounded-xl border border-gray-200/80 bg-white px-4 py-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_8px_16px_-8px_rgba(15,23,42,0.04)]"
        >
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-xs font-medium text-gray-500">{t.label}</p>
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-gray-100 bg-gray-50 text-gray-400">
              {t.icon}
            </span>
          </div>
          {loading ? (
            <span className="skeleton mt-2 block h-6 w-16 rounded" />
          ) : (
            <p
              className={`mt-1.5 text-[26px] font-semibold leading-none tracking-tight ${
                t.value === null
                  ? "text-gray-300"
                  : t.alert
                    ? "text-red-600"
                    : "text-slate-900"
              }`}
            >
              {t.value ?? "—"}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
