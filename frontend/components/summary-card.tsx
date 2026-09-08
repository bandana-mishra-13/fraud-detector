import type { RiskResult } from "@/lib/types";

export default function SummaryCard({ result }: { result: RiskResult }) {
  return (
    <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 px-4 py-3.5">
      <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-indigo-500">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
          <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
        </svg>
        Agent summary
      </p>
      <p className="mt-1.5 text-[13.5px] leading-relaxed text-slate-700">
        {result.summary}
      </p>
      {result.llm_warning && (
        <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[11.5px] text-amber-800">
          LLM summary unavailable — showing deterministic fallback. ({result.llm_warning})
        </p>
      )}
    </div>
  );
}
