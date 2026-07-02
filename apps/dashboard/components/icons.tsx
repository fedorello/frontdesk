import type { ReactNode } from "react";

export type IconName =
  | "overview"
  | "conversations"
  | "calendar"
  | "calls"
  | "approvals"
  | "settings"
  | "sun"
  | "moon"
  | "search"
  | "spark"
  | "check"
  | "admin";

const PATHS: Record<IconName, ReactNode> = {
  overview: (
    <>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h14V9.5" />
    </>
  ),
  conversations: <path d="M21 11.5a7.5 7.5 0 0 1-10.9 6.7L4 20l1.8-5.1A7.5 7.5 0 1 1 21 11.5Z" />,
  calendar: (
    <>
      <rect x="3" y="4.5" width="18" height="16" rx="2.5" />
      <path d="M3 9h18M8 3v3M16 3v3" />
    </>
  ),
  calls: (
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z" />
  ),
  approvals: (
    <>
      <path d="M12 3 5 5.5V11c0 4.4 3 7.5 7 9 4-1.5 7-4.6 7-9V5.5L12 3Z" />
      <path d="m9 11.5 2 2 4-4" />
    </>
  ),
  settings: (
    <>
      <path d="M4 7h11M19 7h1M4 17h7M15 17h5" />
      <circle cx="17" cy="7" r="2" />
      <circle cx="13" cy="17" r="2" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" />
    </>
  ),
  moon: <path d="M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5Z" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3-3" />
    </>
  ),
  spark: <path d="M12 3l2.2 6 6 .3-4.7 3.9 1.6 5.8L12 15.8 6.9 19l1.6-5.8L3.8 9.3l6-.3z" />,
  check: <path d="m5 12.5 4.5 4.5L19 7" />,
  admin: (
    <>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </>
  ),
};

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
