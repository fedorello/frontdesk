"use client";

function initials(name?: string, email?: string): string {
  const source = (name ?? "").trim() || (email ?? "").split("@")[0] || "?";
  const parts = source.split(/[\s._-]+/).filter(Boolean);
  const letters = parts.length >= 2 ? `${parts[0][0]}${parts[1][0]}` : source.slice(0, 2);
  return letters.toUpperCase();
}

// The owner's avatar: their Google picture when present, otherwise initials in a brand circle.
export function UserAvatar({
  name,
  email,
  avatar,
  size = 30,
}: {
  name?: string;
  email?: string;
  avatar?: string;
  size?: number;
}) {
  if (avatar) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- a tiny external avatar; Image is overkill
      <img
        src={avatar}
        alt=""
        referrerPolicy="no-referrer"
        width={size}
        height={size}
        className="shrink-0 rounded-full object-cover"
      />
    );
  }
  return (
    <span
      aria-hidden
      className="flex shrink-0 items-center justify-center rounded-full bg-accent font-bold text-accent-contrast"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.4) }}
    >
      {initials(name, email)}
    </span>
  );
}
