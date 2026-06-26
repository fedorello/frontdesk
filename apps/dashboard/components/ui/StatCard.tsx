import { Icon, type IconName } from "@/components/icons";

export type StatTone = "accent" | "pink" | "neutral";

const CHIP: Record<StatTone, string> = {
  accent: "bg-accent-soft text-accent",
  pink: "bg-pink-soft text-pink",
  neutral: "bg-surface-3 text-muted",
};

/** A headline metric: an icon chip, a big number, and a label. */
export function StatCard({
  icon,
  tone,
  label,
  value,
}: {
  icon: IconName;
  tone: StatTone;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-5 shadow-card">
      <span className={`flex h-12 w-12 items-center justify-center rounded-xl ${CHIP[tone]}`}>
        <Icon name={icon} size={22} />
      </span>
      <div>
        <div className="text-3xl font-extrabold leading-none tabular-nums">{value}</div>
        <div className="mt-1.5 text-sm text-muted">{label}</div>
      </div>
    </div>
  );
}
