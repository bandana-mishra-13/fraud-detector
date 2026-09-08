"use client";

import { useEffect, useRef, useState } from "react";
import type { ToolOverrides } from "@/lib/api";

/** The tool universe, matching backend TOOL_ORDER. load_data/apply_filters are
 * locked (the pipeline needs them); the rest are overridable. */
const TOOLS: { id: string; label: string; locked?: boolean }[] = [
  { id: "load_data", label: "Load data", locked: true },
  { id: "apply_filters", label: "Apply filters", locked: true },
  { id: "eda", label: "EDA / profiling" },
  { id: "feature_engineering", label: "Feature engineering" },
  { id: "rule_detection", label: "Rule detection" },
  { id: "ml_anomaly", label: "ML anomaly" },
  { id: "aggregation", label: "Aggregation" },
  { id: "entity_lookup", label: "Entity lookup" },
  { id: "risk_classification", label: "Risk classification" },
];

type Mode = "auto" | "on" | "off";

function SparkleIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
    </svg>
  );
}

const SEG: { mode: Mode; label: string; cls: string }[] = [
  { mode: "auto", label: "Auto", cls: "text-indigo-700" },
  { mode: "on", label: "On", cls: "text-emerald-700" },
  { mode: "off", label: "Off", cls: "text-gray-500" },
];

export default function ToolPicker({
  overrides,
  onChange,
  disabled,
}: {
  overrides: ToolOverrides;
  onChange: (next: ToolOverrides) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  const count = Object.keys(overrides).length;
  const isCustom = count > 0;

  const setMode = (tool: string, mode: Mode) => {
    const next = { ...overrides };
    if (mode === "auto") delete next[tool];
    else next[tool] = mode;
    onChange(next);
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={`inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-[11.5px] transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 ${
          isCustom
            ? "text-indigo-600 hover:bg-indigo-50"
            : "text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        }`}
        title="Choose which tools the agent may use"
      >
        <SparkleIcon />
        {isCustom ? `Tools: Custom (${count})` : "Tools: Auto"}
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true" className={open ? "rotate-180 transition-transform" : "transition-transform"}>
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Tool selection"
          className="absolute left-0 top-full z-30 mt-2 max-h-[60vh] w-72 overflow-y-auto rounded-xl border border-gray-200 bg-white p-2 shadow-[0_8px_28px_-8px_rgba(15,23,42,0.25)]"
        >
          <div className="flex items-center justify-between px-1.5 pb-1.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
              Tool selection
            </p>
            {isCustom && (
              <button
                type="button"
                onClick={() => onChange({})}
                className="text-[11px] font-medium text-indigo-600 hover:underline"
              >
                Reset to Auto
              </button>
            )}
          </div>
          <p className="px-1.5 pb-2 text-[11px] leading-snug text-gray-400">
            Auto lets the agent decide per query. Override any tool to force it
            on or off — dependencies resolve automatically.
          </p>

          <div className="space-y-0.5">
            {TOOLS.map((t) => {
              const mode: Mode = (overrides[t.id] as Mode) ?? "auto";
              return (
                <div
                  key={t.id}
                  className="flex items-center justify-between gap-2 rounded-lg px-1.5 py-1"
                >
                  <span className={`text-[12.5px] ${t.locked ? "text-gray-400" : "text-slate-700"}`}>
                    {t.label}
                    {t.locked && <span className="ml-1 text-[10px] text-gray-300">always</span>}
                  </span>
                  {t.locked ? (
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-[10.5px] font-medium text-gray-400">
                      required
                    </span>
                  ) : (
                    <div className="inline-flex rounded-md bg-gray-100 p-0.5">
                      {SEG.map((s) => (
                        <button
                          key={s.mode}
                          type="button"
                          onClick={() => setMode(t.id, s.mode)}
                          className={`rounded px-2 py-0.5 text-[11px] font-medium transition-colors duration-100 ${
                            mode === s.mode
                              ? `bg-white shadow-[0_1px_2px_rgba(15,23,42,0.1)] ${s.cls}`
                              : "text-gray-400 hover:text-gray-600"
                          }`}
                        >
                          {s.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
