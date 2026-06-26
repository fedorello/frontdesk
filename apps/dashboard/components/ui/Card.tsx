import type { ReactNode } from "react";

/** A surface panel: the design's rounded card with a soft shadow. */
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-line bg-surface shadow-card ${className}`}>
      {children}
    </div>
  );
}
