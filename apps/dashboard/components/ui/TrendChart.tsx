import type { DailyCount } from "@/app/lib/api";

// A small, dependency-free SVG trend chart for a daily-count series. Inline SVG keeps it
// CSP-safe (no eval), themeable (currentColor + Tailwind tokens), and accessible. We render
// our own rather than pull a charting library for these simple trends (KISS).

const WIDTH = 300;
const HEIGHT = 64;
const PAD = 4;

function points(data: DailyCount[]): { line: string; area: string; max: number } {
  const max = Math.max(1, ...data.map((d) => d.count));
  const span = data.length > 1 ? data.length - 1 : 1;
  const x = (index: number) => PAD + (index / span) * (WIDTH - 2 * PAD);
  const y = (count: number) => HEIGHT - PAD - (count / max) * (HEIGHT - 2 * PAD);
  const coords = data.map((d, index) => `${x(index).toFixed(1)},${y(d.count).toFixed(1)}`);
  const line = coords.join(" ");
  const area = `${PAD},${HEIGHT - PAD} ${line} ${(WIDTH - PAD).toFixed(1)},${HEIGHT - PAD}`;
  return { line, area, max };
}

/** A labelled trend card with an inline SVG line+area chart. */
export function TrendChart({ label, data }: { label: string; data: DailyCount[] }) {
  const total = data.reduce((sum, d) => sum + d.count, 0);
  const { line, area } = points(data);

  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold text-muted">{label}</span>
        <span className="text-lg font-extrabold tabular-nums">{total}</span>
      </div>
      <div className="mt-3 text-accent">
        {data.length === 0 ? (
          <div className="h-16 rounded-lg bg-surface-3" aria-hidden />
        ) : (
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="h-16 w-full"
            preserveAspectRatio="none"
            role="img"
            aria-label={label}
          >
            <polygon points={area} fill="currentColor" fillOpacity={0.12} />
            <polyline
              points={line}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        )}
      </div>
    </div>
  );
}
