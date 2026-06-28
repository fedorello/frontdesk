const Check = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="3"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <path d="m5 12 5 5L20 6" />
  </svg>
);

// A horizontal stepper: numbered circles joined by lines, with a label under each.
// Completed steps show a check, the current step is highlighted, the rest are muted.
export function StepIndicator({ labels, current }: { labels: string[]; current: number }) {
  return (
    <ol className="flex items-start" aria-label="steps">
      {labels.map((label, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <li key={label} className="relative flex flex-1 flex-col items-center">
            {index > 0 && (
              <span
                aria-hidden
                className={`absolute right-1/2 top-3.5 h-0.5 w-full -translate-y-1/2 ${
                  index <= current ? "bg-accent" : "bg-line-strong"
                }`}
              />
            )}
            <span
              aria-current={active ? "step" : undefined}
              className={`relative z-10 flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition ${
                done
                  ? "bg-accent text-accent-contrast"
                  : active
                    ? "bg-accent text-accent-contrast ring-4 ring-accent/20"
                    : "border border-line-strong bg-surface text-muted"
              }`}
            >
              {done ? <Check /> : index + 1}
            </span>
            <span
              className={`mt-1.5 px-1 text-center text-[11px] leading-tight ${
                active ? "font-semibold text-ink" : done ? "text-accent" : "text-muted"
              }`}
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
