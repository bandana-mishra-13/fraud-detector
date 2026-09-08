"use client";

export default function Pagination({
  page,
  pageCount,
  total,
  shownFrom,
  shownTo,
  onPage,
}: {
  page: number; // 1-based
  pageCount: number;
  total: number;
  shownFrom: number;
  shownTo: number;
  onPage: (p: number) => void;
}) {
  if (pageCount <= 1) return null;

  const btn =
    "inline-flex h-6 w-6 items-center justify-center rounded-md border border-gray-200 bg-white text-gray-500 transition-colors duration-100 hover:border-indigo-200 hover:text-indigo-600 disabled:opacity-40 disabled:hover:border-gray-200 disabled:hover:text-gray-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600";

  return (
    <div className="flex items-center justify-between border-t border-gray-100 px-4 py-2.5">
      <p className="text-[11.5px] tabular-nums text-gray-400">
        {shownFrom}–{shownTo} of {total}
      </p>
      <div className="flex items-center gap-1.5">
        <button type="button" aria-label="Previous page" className={btn} disabled={page <= 1} onClick={() => onPage(page - 1)}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m15 6-6 6 6 6" />
          </svg>
        </button>
        <span className="min-w-[64px] text-center text-[11.5px] tabular-nums text-gray-500">
          Page {page} / {pageCount}
        </span>
        <button type="button" aria-label="Next page" className={btn} disabled={page >= pageCount} onClick={() => onPage(page + 1)}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m9 6 6 6-6 6" />
          </svg>
        </button>
      </div>
    </div>
  );
}
