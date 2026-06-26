import type { ReactNode } from "react";

import { Icon, type IconName } from "@/components/icons";

/** The design's centered empty state: an icon badge, a title, body, and optional action. */
export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon: IconName;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-3xl bg-accent-soft text-accent">
        <Icon name={icon} size={36} />
      </div>
      <h2 className="text-xl font-extrabold">{title}</h2>
      {body !== undefined && <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>}
      {action !== undefined && <div className="mt-5 flex justify-center gap-2">{action}</div>}
    </div>
  );
}
