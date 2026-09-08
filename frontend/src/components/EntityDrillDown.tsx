"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BrainCircuit,
  Building2,
  Database,
  FileSearch,
  Network,
  ShieldAlert,
  Users,
} from "lucide-react";
import {
  ExecutionPlan,
  Flag,
  ParsedIntent,
  RiskResult,
  SynthesizedResult,
} from "@/lib/api";

type EvidenceRecord = Record<string, unknown>;

interface EntityDrillDownProps {
  riskResult?: RiskResult | null;
  flags: Flag[];
  executionPlan: ExecutionPlan;
  parsedIntent: ParsedIntent;
  synthesizedResult?: SynthesizedResult | null;
  edaSummary?: Record<string, unknown> | null;
  onSelectFlag?: (flag: Flag) => void;
}

interface Metric {
  label: string;
  value: string;
}

interface FlagEvidenceMetrics {
  flagId: string;
  label: string;
  metrics: Metric[];
}

function asRecord(value: unknown): EvidenceRecord | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as EvidenceRecord)
    : null;
}

function asFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asEntityId(value: string | null | undefined): string | null {
  const entity = value?.trim();
  return entity ? entity : null;
}

function uniqueValues(values: Array<string | null | undefined>): string[] {
  const unique = new Set<string>();
  for (const value of values) {
    const cleanValue = asEntityId(value);
    if (cleanValue) unique.add(cleanValue);
  }
  return Array.from(unique);
}

function getEvidenceCurrency(record: EvidenceRecord | null): string | null {
  if (!record) return null;

  const directCurrencyKeys = ["currency", "amount_currency", "payment_currency", "receiving_currency"];
  for (const key of directCurrencyKeys) {
    const currency = record[key];
    if (typeof currency === "string" && currency.trim()) return currency.trim();
  }

  const volumeDistribution = asRecord(record.volume_distribution);
  return volumeDistribution ? getEvidenceCurrency(volumeDistribution) : null;
}

function formatMonetaryValue(value: number, currency: string | null): string {
  const formattedValue = value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return currency ? `${currency} ${formattedValue}` : formattedValue;
}

function formatScore(value: number | null | undefined, digits = 2): string {
  return value !== null && value !== undefined && Number.isFinite(value)
    ? value.toFixed(digits)
    : "Unavailable";
}

function getNumberMetric(record: EvidenceRecord | null, key: string): number | null {
  return record ? asFiniteNumber(record[key]) : null;
}

export function getEntityCandidates(
  riskResult: RiskResult | null | undefined,
  executionPlan: ExecutionPlan,
  parsedIntent: ParsedIntent,
  flags: Flag[],
): string[] {
  return uniqueValues([
    riskResult?.entity_id,
    ...executionPlan.target_entities,
    ...parsedIntent.entities,
    ...flags.map((flag) => flag.entity_id),
  ]);
}

export function getEntityFlags(flags: Flag[], entityId: string): Flag[] {
  return flags.filter((flag) => flag.entity_id === entityId);
}

export function getEntityTransactionIds(flags: Flag[]): string[] {
  return Array.from(new Set(flags.flatMap((flag) => flag.transaction_ids)));
}

export function isSingleEntityQueryFor(
  entityId: string,
  executionPlan: ExecutionPlan,
  parsedIntent: ParsedIntent,
): boolean {
  const explicitlyRequestedEntities = uniqueValues([
    ...executionPlan.target_entities,
    ...parsedIntent.entities,
  ]);
  return explicitlyRequestedEntities.length === 1 && explicitlyRequestedEntities[0] === entityId;
}

function getEntitySummaryMetrics(
  riskResult: RiskResult | null,
  edaSummary: Record<string, unknown> | null | undefined,
  isEntityScoped: boolean,
): Metric[] {
  const metrics: Metric[] = [];
  const riskEvidence = asRecord(riskResult?.evidence_summary);

  const riskTransactionCount = getNumberMetric(riskEvidence, "total_transactions");
  if (riskTransactionCount !== null) {
    metrics.push({ label: "Transactions reviewed", value: riskTransactionCount.toLocaleString() });
  }

  if (!isEntityScoped) return metrics;

  const eda = asRecord(edaSummary);
  const edaCurrency = getEvidenceCurrency(eda);
  const transactionCount = getNumberMetric(eda, "total_transactions");
  const totalVolume = getNumberMetric(eda, "total_volume");
  const counterparties = getNumberMetric(eda, "distinct_counterparties");

  if (transactionCount !== null && riskTransactionCount === null) {
    metrics.push({ label: "Transactions reviewed", value: transactionCount.toLocaleString() });
  }
  if (totalVolume !== null) {
    metrics.push({ label: "Reported volume", value: formatMonetaryValue(totalVolume, edaCurrency) });
  }
  if (counterparties !== null) {
    metrics.push({ label: "Distinct counterparties", value: counterparties.toLocaleString() });
  }

  return metrics;
}

function getFlagEvidenceMetrics(flags: Flag[]): FlagEvidenceMetrics[] {
  return flags
    .map((flag) => {
      const evidence = asRecord(flag.evidence);
      const evidenceCurrency = getEvidenceCurrency(evidence);
      const metrics: Metric[] = [];
      const addMetric = (
        key: string,
        label: string,
        formatter: (value: number) => string = (value) => value.toLocaleString(),
      ) => {
        const value = getNumberMetric(evidence, key);
        if (value !== null) metrics.push({ label, value: formatter(value) });
      };

      addMetric("tx_count", "Cited transactions");
      addMetric("total_amount", "Reported amount", (value) => formatMonetaryValue(value, evidenceCurrency));
      addMetric("in_amount", "Inbound amount", (value) => formatMonetaryValue(value, evidenceCurrency));
      addMetric("out_amount", "Outbound amount", (value) => formatMonetaryValue(value, evidenceCurrency));
      addMetric("pass_through_ratio", "Pass-through ratio", (value) => `${(value * 100).toFixed(1)}%`);
      addMetric("time_delta_minutes", "Time delta", (value) => `${value.toLocaleString()} min`);
      addMetric("time_span_hours", "Time span", (value) => `${value.toLocaleString()} hrs`);
      addMetric("distinct_recipients", "Distinct recipients");

      return metrics.length > 0
        ? { flagId: flag.flag_id, label: flag.typology || flag.rule_name, metrics }
        : null;
    })
    .filter((entry): entry is FlagEvidenceMetrics => entry !== null);
}

function getCounterpartyIds(flags: Flag[]): string[] {
  const counterparties: string[] = [];
  const recipientKeys = ["sample_recipients", "recipient_ids", "counterparty_ids"];

  for (const flag of flags) {
    const evidence = asRecord(flag.evidence);
    if (!evidence) continue;

    for (const key of recipientKeys) {
      const values = evidence[key];
      if (!Array.isArray(values)) continue;
      for (const value of values) {
        if (typeof value === "string" && value.trim()) counterparties.push(value.trim());
      }
    }
  }

  return Array.from(new Set(counterparties));
}

function getNarratives(
  entityId: string,
  riskResult: RiskResult | null,
  synthesizedResult: SynthesizedResult | null | undefined,
  flags: Flag[],
  isSingleEntityQuery: boolean,
): string[] {
  const narratives = [riskResult?.summary, ...flags.map((flag) => flag.reason)];

  if (isSingleEntityQuery) {
    narratives.push(synthesizedResult?.executive_summary);
  }
  narratives.push(
    ...((synthesizedResult?.key_findings ?? []).filter((finding) => finding.includes(entityId))),
  );

  return Array.from(new Set(narratives.filter((narrative): narrative is string => Boolean(narrative))));
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/10 bg-slate-950/35 px-4 py-5 text-center text-xs text-slate-500">
      {message}
    </div>
  );
}

export function EntityDrillDown({
  riskResult,
  flags,
  executionPlan,
  parsedIntent,
  synthesizedResult,
  edaSummary,
  onSelectFlag,
}: EntityDrillDownProps) {
  const candidates = useMemo(
    () => getEntityCandidates(riskResult, executionPlan, parsedIntent, flags),
    [riskResult, executionPlan, parsedIntent, flags],
  );
  const candidateKey = candidates.join("|");
  const [selectedEntity, setSelectedEntity] = useState<string | null>(candidates[0] ?? null);

  useEffect(() => {
    setSelectedEntity((current) => (
      current && candidates.includes(current) ? current : candidates[0] ?? null
    ));
  }, [candidateKey, candidates]);

  const entityId = selectedEntity && candidates.includes(selectedEntity)
    ? selectedEntity
    : candidates[0] ?? null;

  if (!entityId) {
    return (
      <section className="space-y-4" aria-labelledby="entity-drill-down-heading">
        <div>
          <h2 id="entity-drill-down-heading" className="text-base font-bold text-white">Entity 360° View</h2>
          <p className="mt-1 text-xs text-slate-400">Entity-specific risk evidence is shown only when an explicit entity is available.</p>
        </div>
        <EmptyState message="No entity-specific findings available for this investigation." />
      </section>
    );
  }

  const entityFlags = getEntityFlags(flags, entityId);
  const citedTransactions = getEntityTransactionIds(entityFlags);
  const scopedRiskResult = riskResult?.entity_id === entityId ? riskResult : null;
  const isSingleEntityQuery = isSingleEntityQueryFor(entityId, executionPlan, parsedIntent);
  const summaryMetrics = getEntitySummaryMetrics(scopedRiskResult, edaSummary, isSingleEntityQuery);
  const evidenceMetrics = getFlagEvidenceMetrics(entityFlags);
  const counterparties = getCounterpartyIds(entityFlags);
  const recipientCounts = entityFlags
    .map((flag) => getNumberMetric(asRecord(flag.evidence), "distinct_recipients"))
    .filter((count): count is number => count !== null);
  const narratives = getNarratives(
    entityId,
    scopedRiskResult,
    synthesizedResult,
    entityFlags,
    isSingleEntityQuery,
  );

  return (
    <section className="space-y-4" aria-labelledby="entity-drill-down-heading">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h2 id="entity-drill-down-heading" className="text-base font-bold text-white">Entity 360° View</h2>
          <p className="mt-1 text-xs text-slate-400">Focused evidence for the selected customer or account.</p>
        </div>
        {candidates.length > 1 && (
          <div className="flex flex-wrap gap-2" aria-label="Select entity for drill-down">
            {candidates.map((candidate) => (
              <button
                key={candidate}
                type="button"
                onClick={() => setSelectedEntity(candidate)}
                aria-pressed={candidate === entityId}
                className={`rounded-lg border px-3 py-1.5 font-mono text-xs transition-colors ${
                  candidate === entityId
                    ? "border-sky-400/60 bg-sky-500/15 text-sky-200"
                    : "border-white/10 bg-slate-900/60 text-slate-400 hover:border-sky-500/40 hover:text-slate-200"
                }`}
              >
                {candidate}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="glass-panel rounded-2xl border border-sky-500/20 p-5 shadow-xl">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 p-3 text-white shadow-lg shadow-sky-500/20">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Selected entity</p>
              <h3 className="text-xl font-black text-white">{entityId}</h3>
              <p className="mt-1 text-xs text-slate-400">Intent: <span className="font-mono text-sky-300">{parsedIntent.intent}</span></p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-white/5 bg-slate-950/45 px-3 py-2">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">Risk tier</p>
              <p className="mt-1 text-sm font-bold text-rose-300">{scopedRiskResult?.risk_tier ?? "Unavailable"}</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-slate-950/45 px-3 py-2">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">Risk score</p>
              <p className="mt-1 font-mono text-sm font-bold text-white">{formatScore(scopedRiskResult?.risk_score, 4)}</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-slate-950/45 px-3 py-2">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">Rule score</p>
              <p className="mt-1 font-mono text-sm font-bold text-white">{formatScore(scopedRiskResult?.rule_score)}</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-slate-950/45 px-3 py-2">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">ML score</p>
              <p className="mt-1 font-mono text-sm font-bold text-white">{formatScore(scopedRiskResult?.ml_score)}</p>
            </div>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3 border-t border-white/10 pt-4 sm:grid-cols-4">
          <div className="flex items-center gap-2 text-xs text-slate-400"><ShieldAlert className="h-4 w-4 text-rose-400" />{entityFlags.length} relevant flags</div>
          <div className="flex items-center gap-2 text-xs text-slate-400"><Database className="h-4 w-4 text-sky-400" />{citedTransactions.length} cited transactions</div>
          <div className="flex items-center gap-2 text-xs text-slate-400"><Activity className="h-4 w-4 text-amber-400" />{new Set(entityFlags.map((flag) => flag.typology || flag.rule_name)).size} typologies</div>
          <div className="flex items-center gap-2 text-xs text-slate-400"><FileSearch className="h-4 w-4 text-emerald-400" />{isSingleEntityQuery ? "Single-entity investigation" : scopedRiskResult ? "Scoped risk result" : "Flag-derived scope"}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="glass-panel rounded-2xl border border-rose-500/15 p-5" aria-labelledby="entity-typologies-heading">
          <div className="mb-4 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
            <h3 id="entity-typologies-heading" className="text-sm font-bold text-white">Triggered Typologies</h3>
          </div>
          {entityFlags.length > 0 ? (
            <div className="space-y-2">
              {entityFlags.map((flag) => (
                <button
                  key={flag.flag_id}
                  type="button"
                  onClick={() => onSelectFlag?.(flag)}
                  disabled={!onSelectFlag}
                  className="w-full rounded-xl border border-white/5 bg-slate-950/35 p-3 text-left transition-colors enabled:hover:border-sky-500/40 enabled:hover:bg-slate-900/80 disabled:cursor-default"
                  aria-label={`Open evidence for ${flag.typology || flag.rule_name}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold text-slate-100">{flag.typology || flag.rule_name}</p>
                      <p className="mt-0.5 text-[11px] text-slate-400">{flag.rule_name}</p>
                    </div>
                    <span className="rounded border border-rose-400/25 bg-rose-500/10 px-2 py-0.5 text-[10px] font-mono text-rose-200">{flag.severity}</span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-300">{flag.reason}</p>
                  <p className="mt-2 text-[10px] font-mono text-sky-300">{flag.transaction_ids.length} cited transaction IDs{onSelectFlag ? " · Open evidence" : ""}</p>
                </button>
              ))}
            </div>
          ) : <EmptyState message="No entity-specific findings available." />}
        </article>

        <article className="glass-panel rounded-2xl border border-sky-500/15 p-5" aria-labelledby="entity-transactions-heading">
          <div className="mb-4 flex items-center gap-2">
            <Database className="h-4 w-4 text-sky-400" />
            <h3 id="entity-transactions-heading" className="text-sm font-bold text-white">Transaction Evidence</h3>
          </div>
          {citedTransactions.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {citedTransactions.map((transactionId) => (
                <span key={transactionId} className="rounded-lg border border-sky-500/30 bg-sky-950/45 px-2.5 py-1 text-xs font-mono text-sky-200">{transactionId}</span>
              ))}
            </div>
          ) : <EmptyState message="No cited transactions available for this entity." />}
        </article>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="glass-panel rounded-2xl border border-indigo-500/15 p-5" aria-labelledby="entity-metrics-heading">
          <div className="mb-4 flex items-center gap-2">
            <BrainCircuit className="h-4 w-4 text-indigo-300" />
            <h3 id="entity-metrics-heading" className="text-sm font-bold text-white">Entity Metrics</h3>
          </div>
          {summaryMetrics.length > 0 || evidenceMetrics.length > 0 ? (
            <div className="space-y-3">
              {summaryMetrics.length > 0 && (
                <div className="grid grid-cols-2 gap-2">
                  {summaryMetrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
                </div>
              )}
              {evidenceMetrics.map((group) => (
                <div key={group.flagId} className="rounded-xl border border-white/5 bg-slate-950/35 p-3">
                  <p className="mb-2 text-[10px] font-mono uppercase tracking-wider text-indigo-300">{group.label} evidence</p>
                  <div className="grid grid-cols-2 gap-2">
                    {group.metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
                  </div>
                </div>
              ))}
            </div>
          ) : <EmptyState message="No entity metrics available." />}
        </article>

        <article className="glass-panel rounded-2xl border border-amber-500/15 p-5" aria-labelledby="entity-counterparty-heading">
          <div className="mb-4 flex items-center gap-2">
            <Network className="h-4 w-4 text-amber-300" />
            <h3 id="entity-counterparty-heading" className="text-sm font-bold text-white">Counterparty & Flow Evidence</h3>
          </div>
          {counterparties.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {counterparties.map((counterparty) => (
                <span key={counterparty} className="rounded-lg border border-amber-400/25 bg-amber-500/10 px-2.5 py-1 text-xs font-mono text-amber-100">{counterparty}</span>
              ))}
            </div>
          ) : <EmptyState message="Counterparty details unavailable." />}
          {recipientCounts.length > 0 && (
            <p className="mt-3 flex items-center gap-2 text-xs text-slate-400"><Users className="h-4 w-4 text-amber-300" />Rule evidence reports {Math.max(...recipientCounts)} distinct recipients.</p>
          )}
        </article>
      </div>

      <article className="glass-panel rounded-2xl border border-emerald-500/15 p-5" aria-labelledby="entity-narrative-heading">
        <div className="mb-4 flex items-center gap-2">
          <FileSearch className="h-4 w-4 text-emerald-300" />
          <h3 id="entity-narrative-heading" className="text-sm font-bold text-white">Supporting Investigative Narrative</h3>
        </div>
        {narratives.length > 0 ? (
          <div className="space-y-2">
            {narratives.slice(0, 4).map((narrative) => (
              <p key={narrative} className="rounded-xl border border-white/5 bg-slate-950/35 p-3 text-xs leading-relaxed text-slate-300">{narrative}</p>
            ))}
          </div>
        ) : <EmptyState message="No entity-specific narrative is available." />}
      </article>
    </section>
  );
}

function MetricCard({ metric }: { metric: Metric }) {
  return (
    <div className="rounded-lg border border-white/5 bg-slate-900/55 p-2.5">
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{metric.label}</p>
      <p className="mt-1 text-xs font-mono font-semibold text-slate-100">{metric.value}</p>
    </div>
  );
}
