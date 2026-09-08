import Logo from "./logo";
import StatusPill from "./status-pill";

export default function Header() {
  return (
    <header className="sticky top-0 z-20 h-14 border-b border-gray-200/80 bg-white/85 backdrop-blur-md">
      <div className="flex h-full items-center justify-between px-4 sm:px-5">
        <div className="flex items-center gap-2.5">
          <Logo size={26} />
          <span className="text-[15px] font-semibold tracking-tight text-slate-900">
            Argus
          </span>
          <span className="mt-px hidden rounded-full border border-gray-200/80 bg-gray-50 px-2 py-0.5 text-[11px] font-medium text-gray-500 sm:inline">
            AML Intelligence
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span
            className="hidden items-center gap-1.5 rounded-full border border-gray-200/80 bg-white px-2.5 py-1 text-xs font-medium text-gray-500 md:inline-flex"
            title="IBM Transactions for Anti-Money Laundering — Kaggle"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
              <ellipse cx="12" cy="6" rx="7" ry="2.5" />
              <path d="M5 6v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6" />
              <path d="M5 12v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-6" />
            </svg>
            IBM AML · HI-Small
          </span>
          <StatusPill />
        </div>
      </div>
    </header>
  );
}
