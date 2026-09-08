"use client";

import { useState } from "react";
import { fmtCompact, fmtInt } from "@/lib/format";

/** Vertical column chart (time series) — single indigo hue, hover tooltip. */
export function ColumnChart({
  data,
  ariaLabel,
}: {
  data: { label: string; value: number }[];
  ariaLabel: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div aria-label={ariaLabel} role="img" className="relative">
      {hover !== null && (
        <div
          className="pointer-events-none absolute -top-1 z-10 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-md border border-gray-200 bg-white px-2 py-1 text-[11px] text-slate-700 shadow-sm"
          style={{ left: `${((hover + 0.5) / data.length) * 100}%` }}
        >
          {data[hover].label} · {fmtInt(data[hover].value)}
        </div>
      )}
      <div className="flex h-32 items-end gap-[2px]" onMouseLeave={() => setHover(null)}>
        {data.map((d, i) => (
          <div
            key={d.label}
            onMouseEnter={() => setHover(i)}
            className="group flex h-full flex-1 cursor-default items-end"
          >
            <div
              className={`w-full rounded-t-[3px] transition-colors duration-100 ${
                hover === i ? "bg-indigo-600" : "bg-indigo-500/80"
              }`}
              style={{ height: `${Math.max((d.value / max) * 100, 2)}%` }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[10.5px] text-gray-400">
        <span>{data[0].label}</span>
        <span>{data[data.length - 1].label}</span>
      </div>
    </div>
  );
}

/** Horizontal bar list — direct-labeled, optional per-row status colors. */
export function BarList({
  data,
  ariaLabel,
}: {
  data: { label: string; value: number; color?: string; dot?: string }[];
  ariaLabel: string;
}) {
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div aria-label={ariaLabel} role="img" className="space-y-2.5">
      {data.map((d) => (
        <div key={d.label} className="flex items-center gap-3">
          <span className="flex w-28 shrink-0 items-center gap-1.5 truncate text-[12px] text-slate-600">
            {d.dot && <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${d.dot}`} />}
            {d.label}
          </span>
          <span className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
            <span
              className={`block h-full rounded-full ${d.color ?? "bg-indigo-500/80"}`}
              style={{ width: `${Math.max((d.value / max) * 100, 1)}%` }}
            />
          </span>
          <span className="w-14 shrink-0 text-right text-[12px] tabular-nums text-slate-600">
            {fmtCompact(d.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-200/80 bg-white p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
        {title}
      </h3>
      {children}
    </div>
  );
}
