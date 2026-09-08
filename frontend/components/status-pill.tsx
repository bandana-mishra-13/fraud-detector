"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/config";

type Status = "checking" | "online" | "offline";

const STYLES: Record<Status, { pill: string; label: string }> = {
  checking: {
    pill: "border-gray-200 bg-white text-gray-500",
    label: "Checking API…",
  },
  online: {
    pill: "border-emerald-200/80 bg-emerald-50 text-emerald-700",
    label: "API online",
  },
  offline: {
    pill: "border-red-200/80 bg-red-50 text-red-600",
    label: "API offline",
  },
};

function Dot({ status }: { status: Status }) {
  if (status === "online") {
    return (
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
      </span>
    );
  }
  return (
    <span
      className={`h-1.5 w-1.5 rounded-full ${
        status === "checking" ? "animate-pulse bg-gray-400" : "bg-red-500"
      }`}
    />
  );
}

export default function StatusPill() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let alive = true;

    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
        if (alive) setStatus(res.ok ? "online" : "offline");
      } catch {
        if (alive) setStatus("offline");
      }
    };

    check();
    const id = setInterval(check, 15_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const s = STYLES[status];

  return (
    <span
      role="status"
      title={`${API_BASE}/health`}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${s.pill}`}
    >
      <Dot status={status} />
      {s.label}
    </span>
  );
}
