// The Tovayo brand mark: a chat-bubble "front desk" with a friendly face.
// Uses the theme's accent/pink tokens so it adapts to light and dark.
export function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden
      style={{ display: "block" }}
    >
      <path
        d="M11 30.5 8 36.5l-.2-6.1A8 8 0 0 1 4 23.5v-10A8 8 0 0 1 12 5.5h16a8 8 0 0 1 8 8v10a8 8 0 0 1-8 8z"
        fill="var(--accent)"
      />
      <circle cx="12.5" cy="19" r="2.1" fill="var(--pink)" opacity=".6" />
      <circle cx="27.5" cy="19" r="2.1" fill="var(--pink)" opacity=".6" />
      <circle cx="15.6" cy="16" r="2.5" fill="#fff" />
      <circle cx="24.4" cy="16" r="2.5" fill="#fff" />
      <path
        d="M14.5 21.5c1.5 2.2 3.4 3.2 5.5 3.2s4-1 5.5-3.2"
        stroke="#fff"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
    </svg>
  );
}
