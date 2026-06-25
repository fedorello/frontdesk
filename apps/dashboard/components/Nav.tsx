import Link from "next/link";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/calendar", label: "Calendar" },
  { href: "/conversations", label: "Conversations" },
  { href: "/approvals", label: "Approvals" },
  { href: "/settings", label: "Settings" },
] as const;

export function Nav() {
  return (
    <nav className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-1 px-6 py-3 text-sm">
        <span className="mr-2 font-semibold">Frontdesk</span>
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-md px-3 py-1.5 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-100"
          >
            {link.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
