"use client";

// Prev / "page X of Y" / Next. Pages are zero-based; the label is shown one-based.
export function Pagination({
  page,
  pageCount,
  onPage,
  prevLabel,
  nextLabel,
}: {
  page: number;
  pageCount: number;
  onPage: (page: number) => void;
  prevLabel: string;
  nextLabel: string;
}) {
  const button =
    "rounded-lg border border-line-strong px-3 py-1.5 text-sm font-medium transition hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <div className="mt-5 flex items-center justify-center gap-4">
      <button
        type="button"
        onClick={() => onPage(page - 1)}
        disabled={page <= 0}
        className={button}
      >
        {prevLabel}
      </button>
      <span className="text-sm tabular-nums text-muted">
        {page + 1} / {pageCount}
      </span>
      <button
        type="button"
        onClick={() => onPage(page + 1)}
        disabled={page >= pageCount - 1}
        className={button}
      >
        {nextLabel}
      </button>
    </div>
  );
}
