"use client";

import React from "react";
import { BarChart3, PieChart, TrendingUp } from "lucide-react";
import { Flag, RiskTier } from "@/lib/api";

type UnknownRecord = Record<string, unknown>;

interface AmountBucket {
  label: string;
  count: number;
}

interface AmountDistribution {
  currency: string;
  buckets: AmountBucket[];
}

interface VelocityPoint {
  label: string;
  count: number;
}

interface AnalyticsChartsProps {
  edaSummary?: Record<string, unknown> | null;
  flags: Flag[];
}

const RISK_TIERS: RiskTier[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

const RISK_TIER_COLORS: Record<RiskTier, string> = {
  LOW: "#34d399",
  MEDIUM: "#fbbf24",
  HIGH: "#fb7185",
  CRITICAL: "#c084fc",
};

const CIRCUMFERENCE = 2 * Math.PI * 42;

function asRecord(value: unknown): UnknownRecord | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function asNonNegativeNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0
    ? value
    : null;
}

function formatAmountLabel(label: string): string {
  return label.replace("k", "K").replace("+", "+");
}

function extractBuckets(distribution: UnknownRecord): AmountBucket[] {
  const buckets = asRecord(distribution.buckets);
  if (!buckets) return [];

  return Object.entries(buckets)
    .map(([label, value]) => {
      const count = asNonNegativeNumber(asRecord(value)?.count);
      return count === null ? null : { label: formatAmountLabel(label), count };
    })
    .filter((bucket): bucket is AmountBucket => bucket !== null);
}

export function getAmountDistributions(
  edaSummary?: Record<string, unknown> | null,
): AmountDistribution[] {
  const volumeDistribution = asRecord(edaSummary?.volume_distribution);
  if (!volumeDistribution) return [];

  if (volumeDistribution.is_multi_currency === true) {
    const byCurrency = asRecord(volumeDistribution.by_currency);
    if (!byCurrency) return [];

    return Object.entries(byCurrency)
      .map(([currency, distribution]) => {
        const buckets = extractBuckets(asRecord(distribution) ?? {});
        return buckets.some((bucket) => bucket.count > 0) ? { currency, buckets } : null;
      })
      .filter((distribution): distribution is AmountDistribution => distribution !== null);
  }

  const buckets = extractBuckets(volumeDistribution);
  if (!buckets.some((bucket) => bucket.count > 0)) return [];

  const currency = typeof volumeDistribution.currency === "string"
    ? volumeDistribution.currency
    : "Reported currency";
  return [{ currency, buckets }];
}

export function getRiskTierCounts(flags: Flag[]): Record<RiskTier, number> {
  const counts: Record<RiskTier, number> = {
    LOW: 0,
    MEDIUM: 0,
    HIGH: 0,
    CRITICAL: 0,
  };

  for (const flag of flags) {
    if (RISK_TIERS.includes(flag.severity)) {
      counts[flag.severity] += 1;
    }
  }

  return counts;
}

export function getVelocityTrend(flags: Flag[]): VelocityPoint[] {
  const countsByDay = new Map<string, number>();

  for (const flag of flags) {
    const timestamp = new Date(flag.timestamp);
    if (Number.isNaN(timestamp.getTime())) continue;

    const day = timestamp.toISOString().slice(0, 10);
    countsByDay.set(day, (countsByDay.get(day) ?? 0) + 1);
  }

  const points = Array.from(countsByDay.entries())
    .sort(([first], [second]) => first.localeCompare(second))
    .map(([label, count]) => ({ label, count }));

  // A single activity date does not constitute a meaningful velocity trend.
  return points.length > 1 ? points : [];
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex min-h-48 items-center justify-center rounded-xl border border-dashed border-white/10 bg-slate-950/35 px-5 text-center text-xs leading-relaxed text-slate-500">
      {message}
    </div>
  );
}

function AmountHistogram({ distributions }: { distributions: AmountDistribution[] }) {
  if (distributions.length === 0) {
    return <EmptyChart message="Amount distribution unavailable for this investigation." />;
  }

  return (
    <div className="space-y-5" aria-label="Transaction amount distribution histogram">
      {distributions.map((distribution) => {
        const maximum = Math.max(...distribution.buckets.map((bucket) => bucket.count));
        return (
          <div key={distribution.currency} className="space-y-2">
            <p className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              Currency: {distribution.currency}
            </p>
            <div className="flex h-48 items-end gap-2 border-b border-l border-white/10 px-3 pb-2 pt-5 sm:gap-3">
              {distribution.buckets.map((bucket) => (
                <div key={bucket.label} className="flex h-full min-w-0 flex-1 flex-col justify-end gap-1 text-center">
                  <span className="text-[10px] font-mono text-slate-300">{bucket.count}</span>
                  <div
                    className="rounded-t bg-gradient-to-t from-sky-600 to-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.18)]"
                    style={{ height: `${(bucket.count / maximum) * 100}%` }}
                    title={`${bucket.label}: ${bucket.count} transactions`}
                  />
                  <span className="whitespace-nowrap text-[9px] text-slate-500 sm:text-[10px]">
                    {bucket.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RiskTierDonut({ counts }: { counts: Record<RiskTier, number> }) {
  const total = RISK_TIERS.reduce((sum, tier) => sum + counts[tier], 0);
  if (total === 0) {
    return <EmptyChart message="No risk findings to display for this investigation." />;
  }

  let offset = 0;
  return (
    <div className="grid grid-cols-1 items-center gap-4 sm:grid-cols-[132px_1fr]" aria-label="Risk-tier breakdown">
      <svg viewBox="0 0 120 120" className="mx-auto h-32 w-32" role="img" aria-label={`${total} findings by risk tier`}>
        <circle cx="60" cy="60" r="42" fill="none" stroke="#1e293b" strokeWidth="14" />
        {RISK_TIERS.map((tier) => {
          const length = (counts[tier] / total) * CIRCUMFERENCE;
          const segment = (
            <circle
              key={tier}
              cx="60"
              cy="60"
              r="42"
              fill="none"
              stroke={RISK_TIER_COLORS[tier]}
              strokeWidth="14"
              strokeDasharray={`${length} ${CIRCUMFERENCE - length}`}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
              transform="rotate(-90 60 60)"
            >
              <title>{`${tier}: ${counts[tier]} findings`}</title>
            </circle>
          );
          offset += length;
          return segment;
        })}
        <text x="60" y="57" textAnchor="middle" className="fill-white text-[20px] font-bold">{total}</text>
        <text x="60" y="72" textAnchor="middle" className="fill-slate-400 text-[8px] uppercase">Findings</text>
      </svg>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs" aria-label="Risk-tier legend">
        {RISK_TIERS.map((tier) => (
          <li key={tier} className="flex items-center justify-between gap-2 text-slate-300">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: RISK_TIER_COLORS[tier] }} />
              <span>{tier}</span>
            </span>
            <span className="font-mono text-slate-400">{counts[tier]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function VelocityTrendChart({ points }: { points: VelocityPoint[] }) {
  if (points.length === 0) {
    return <EmptyChart message="Velocity trend unavailable for this investigation." />;
  }

  const maxCount = Math.max(...points.map((point) => point.count), 1);
  const width = 640;
  const height = 220;
  const padding = { top: 20, right: 24, bottom: 42, left: 38 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const coordinates = points.map((point, index) => {
    const x = padding.left + (points.length === 1 ? chartWidth / 2 : (index / (points.length - 1)) * chartWidth);
    const y = padding.top + chartHeight - (point.count / maxCount) * chartHeight;
    return { ...point, x, y };
  });
  const linePath = coordinates.map(({ x, y }, index) => `${index === 0 ? "M" : "L"}${x} ${y}`).join(" ");
  const areaPath = `${linePath} L ${coordinates[coordinates.length - 1].x} ${padding.top + chartHeight} L ${coordinates[0].x} ${padding.top + chartHeight} Z`;

  return (
    <div className="overflow-x-auto" aria-label="Suspicious activity velocity over time">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-56 min-w-[420px] w-full" role="img" aria-label="Daily suspicious finding velocity">
        {[0, 0.5, 1].map((fraction) => {
          const y = padding.top + chartHeight - fraction * chartHeight;
          return (
            <g key={fraction}>
              <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} stroke="#334155" strokeDasharray="3 5" />
              <text x={padding.left - 8} y={y + 3} textAnchor="end" className="fill-slate-500 text-[9px]">{Math.round(maxCount * fraction)}</text>
            </g>
          );
        })}
        <path d={areaPath} fill="rgba(45, 212, 191, 0.12)" />
        <path d={linePath} fill="none" stroke="#2dd4bf" strokeWidth="3" strokeLinejoin="round" />
        {coordinates.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="4" fill="#0f172a" stroke="#5eead4" strokeWidth="2">
              <title>{`${point.label}: ${point.count} flagged findings`}</title>
            </circle>
            <text x={point.x} y={height - 16} textAnchor="middle" className="fill-slate-500 text-[9px]">
              {point.label.slice(5)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export function AnalyticsCharts({ edaSummary, flags }: AnalyticsChartsProps) {
  const distributions = getAmountDistributions(edaSummary);
  const riskTierCounts = getRiskTierCounts(flags);
  const velocityTrend = getVelocityTrend(flags);

  return (
    <section className="space-y-4" aria-labelledby="visual-analytics-heading">
      <div>
        <h2 id="visual-analytics-heading" className="text-base font-bold text-white">Visual Analytics</h2>
        <p className="mt-1 text-xs text-slate-400">Evidence-based distribution, risk-tier, and activity views for this investigation.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="glass-panel rounded-2xl border border-sky-500/15 p-5 shadow-xl" aria-labelledby="amount-distribution-heading">
          <div className="mb-4 flex items-start gap-3">
            <div className="rounded-xl bg-sky-500/10 p-2 text-sky-300"><BarChart3 className="h-4 w-4" /></div>
            <div>
              <h3 id="amount-distribution-heading" className="text-sm font-bold text-white">Amount Distribution</h3>
              <p className="text-[11px] text-slate-400">Transaction counts by EDA amount bucket.</p>
            </div>
          </div>
          <AmountHistogram distributions={distributions} />
        </article>

        <article className="glass-panel rounded-2xl border border-purple-500/15 p-5 shadow-xl" aria-labelledby="risk-tier-heading">
          <div className="mb-4 flex items-start gap-3">
            <div className="rounded-xl bg-purple-500/10 p-2 text-purple-300"><PieChart className="h-4 w-4" /></div>
            <div>
              <h3 id="risk-tier-heading" className="text-sm font-bold text-white">Risk-Tier Breakdown</h3>
              <p className="text-[11px] text-slate-400">Deterministic findings grouped by severity.</p>
            </div>
          </div>
          <RiskTierDonut counts={riskTierCounts} />
        </article>
      </div>

      <article className="glass-panel rounded-2xl border border-emerald-500/15 p-5 shadow-xl" aria-labelledby="velocity-trend-heading">
        <div className="mb-4 flex items-start gap-3">
          <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-300"><TrendingUp className="h-4 w-4" /></div>
          <div>
            <h3 id="velocity-trend-heading" className="text-sm font-bold text-white">Suspicious Activity Velocity</h3>
            <p className="text-[11px] text-slate-400">Flagged findings aggregated by available UTC date.</p>
          </div>
        </div>
        <VelocityTrendChart points={velocityTrend} />
      </article>
    </section>
  );
}
