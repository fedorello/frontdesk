"use client";

import { useEffect, useState } from "react";

// Real destinations are set per environment; these are the production defaults.
const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://app.tovayo.com";
const GITHUB_URL =
  process.env.NEXT_PUBLIC_GITHUB_URL ?? "https://github.com/fedorello/tovayo";

/* ---------- icons ---------- */

const ic = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.9,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const ArrowIcon = () => (
  <svg {...ic} width={17} height={17} strokeWidth={2.4}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);
const CheckIcon = () => (
  <svg {...ic} width={11} height={11} strokeWidth={3.2}>
    <path d="m5 12 5 5L20 6" />
  </svg>
);
const PlusIcon = () => (
  <svg {...ic} width={16} height={16} strokeWidth={2.4}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);
const SunIcon = () => (
  <svg {...ic} width={17} height={17}>
    <circle cx="12" cy="12" r="4.5" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" />
  </svg>
);
const MoonIcon = () => (
  <svg {...ic} width={17} height={17}>
    <path d="M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5Z" />
  </svg>
);
const SparkIcon = () => (
  <svg {...ic} width={20} height={20}>
    <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
    <circle cx="12" cy="12" r="4" />
  </svg>
);
const SettingsIcon = () => (
  <svg {...ic} width={21} height={21}>
    <path d="M4 7h11M19 7h1M4 17h7M15 17h5" />
    <circle cx="17" cy="7" r="2" />
    <circle cx="13" cy="17" r="2" />
  </svg>
);
const MessageIcon = () => (
  <svg {...ic} width={20} height={20}>
    <path d="M21 11.5a7.5 7.5 0 0 1-10.9 6.7L4 20l1.8-5.1A7.5 7.5 0 1 1 21 11.5Z" />
  </svg>
);
const CalendarIcon = () => (
  <svg {...ic} width={20} height={20}>
    <rect x="3" y="4.5" width="18" height="16" rx="2.5" />
    <path d="M3 9h18M8 3v3M16 3v3" />
  </svg>
);
const BellIcon = () => (
  <svg {...ic} width={20} height={20}>
    <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
  </svg>
);
const ClipboardIcon = () => (
  <svg {...ic} width={20} height={20}>
    <rect x="6" y="4" width="12" height="17" rx="2" />
    <path d="M9 4V3h6v1M9 10h6M9 14h4" />
  </svg>
);
const HandIcon = () => (
  <svg {...ic} width={20} height={20}>
    <path d="M18 11V6a2 2 0 0 0-4 0v5M14 10V4a2 2 0 0 0-4 0v7M10 10.5V6a2 2 0 0 0-4 0v8a6 6 0 0 0 12 0v-3a2 2 0 0 0-4 0" />
  </svg>
);
const GlobeIcon = () => (
  <svg {...ic} width={20} height={20}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18Z" />
  </svg>
);
const CodeIcon = () => (
  <svg {...ic} width={21} height={21}>
    <path d="m16 18 6-6-6-6M8 6l-6 6 6 6" />
  </svg>
);
const GithubIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.5 2 2 6.6 2 12.2c0 4.5 2.9 8.3 6.8 9.7.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.4-3.4-1.4-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.6 2.4 1.1 3 .9.1-.7.4-1.1.6-1.4-2.2-.3-4.6-1.1-4.6-5 0-1.1.4-2 1-2.7-.1-.3-.4-1.3.1-2.7 0 0 .8-.3 2.7 1a9.4 9.4 0 0 1 5 0c1.9-1.3 2.7-1 2.7-1 .5 1.4.2 2.4.1 2.7.6.7 1 1.6 1 2.7 0 3.9-2.3 4.7-4.6 5 .4.3.7.9.7 1.9v2.8c0 .3.2.6.7.5 3.9-1.4 6.8-5.2 6.8-9.7C22 6.6 17.5 2 12 2z" />
  </svg>
);

export default function Landing() {
  return (
    <div className="font-sans">
      <Navbar />
      <Hero />
      <Demo />
      <HowItWorks />
      <Features />
      <RunItTwoWays />
      <TrustAndData />
      <Faq />
      <CtaBanner />
      <Footer />
    </div>
  );
}

/* ---------- theme ---------- */

function useTheme(): [boolean, () => void] {
  const [dark, setDark] = useState(true);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync to the no-flash theme on mount
    setDark(document.documentElement.getAttribute("data-theme") === "dark");
  }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.setAttribute(
      "data-theme",
      next ? "dark" : "light",
    );
    try {
      localStorage.setItem("tovayo.theme", next ? "dark" : "light");
    } catch {
      // ignore: private mode / storage disabled — the toggle still applies for the session
    }
  };
  return [dark, toggle];
}

/* ---------- shared bits ---------- */

const primaryBtn =
  "inline-flex items-center gap-2 rounded-xl bg-accent px-6 py-3.5 text-base font-bold text-accent-contrast shadow-card transition hover:opacity-90";
const secondaryBtn =
  "inline-flex items-center gap-2 rounded-xl border border-line-strong bg-surface px-6 py-3.5 text-base font-bold text-ink transition hover:bg-surface-3";

function Section({
  id,
  children,
  className = "",
}: {
  id?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      className={`mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 sm:py-20 ${className}`}
    >
      {children}
    </section>
  );
}

function Heading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-center text-3xl font-extrabold tracking-tight sm:text-4xl">
      {children}
    </h2>
  );
}

/* ---------- navbar ---------- */

function Navbar() {
  const [dark, toggle] = useTheme();
  return (
    <nav className="sticky top-0 z-40 border-b border-line bg-surface/80 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-4 px-5 py-3 sm:px-8">
        <a href="#top" className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-accent text-base font-extrabold text-accent-contrast">
            T
          </span>
          <span className="text-lg font-extrabold tracking-tight">Tovayo</span>
        </a>
        <div className="ml-3 hidden items-center gap-1 md:flex">
          {[
            ["Demo", "#demo"],
            ["How it works", "#how"],
            ["Features", "#features"],
            ["FAQ", "#faq"],
          ].map(([label, href]) => (
            <a
              key={href}
              href={href}
              className="rounded-[9px] px-3 py-2 text-sm font-semibold text-muted transition hover:bg-surface-3"
            >
              {label}
            </a>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2.5">
          <button
            type="button"
            onClick={toggle}
            aria-label="Toggle theme"
            className="flex h-9 w-9 items-center justify-center rounded-[10px] border border-line bg-surface text-muted transition hover:bg-surface-3"
          >
            {dark ? <SunIcon /> : <MoonIcon />}
          </button>
          <a
            href={GITHUB_URL}
            className="hidden rounded-[10px] border border-line-strong bg-surface px-3.5 py-2 text-sm font-bold sm:inline-block"
          >
            View on GitHub
          </a>
          <a
            href={APP_URL}
            className="rounded-[10px] bg-accent px-4 py-2 text-sm font-bold text-accent-contrast"
          >
            Start free
          </a>
        </div>
      </div>
    </nav>
  );
}

/* ---------- hero ---------- */

function Hero() {
  return (
    <header id="top" className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-1/2 top-[-120px] h-[460px] w-[760px] max-w-full -translate-x-1/2 rounded-full bg-accent-soft opacity-80 blur-2xl" />
      <Section className="relative text-center">
        <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-[13px] font-semibold text-muted shadow-card">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          Free &amp; open source · MIT
        </span>
        <h1 className="mx-auto max-w-3xl text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">
          A free <span className="text-accent">AI front desk</span> for your
          small business
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-muted">
          It answers customers, books appointments, and sends reminders — 24/7,
          in their language. Use the open source, or let us host it for you.
          Both free.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <a href={APP_URL} className={primaryBtn}>
            Start free <ArrowIcon />
          </a>
          <a href={GITHUB_URL} className={secondaryBtn}>
            <GithubIcon /> View on GitHub
          </a>
        </div>
        <p className="mt-5 text-[13.5px] font-semibold text-faint">
          Free &amp; unlimited · Open source · No card required
        </p>
      </Section>
    </header>
  );
}

/* ---------- demo (illustrative sample; the live widget is wired in phase 2) ---------- */

const SAMPLE: {
  who: "user" | "bot";
  text: string;
  trace?: { kind: string; text: string }[];
}[] = [
  { who: "user", text: "Hi! Can I get a haircut tomorrow afternoon?" },
  {
    who: "bot",
    text: "Of course! 💇 Tomorrow afternoon I have 14:00, 14:30 and 15:15 open. Which works?",
    trace: [
      { kind: "think", text: "Customer wants a haircut tomorrow PM" },
      {
        kind: "tool",
        text: 'find_availability(service: "Haircut", around: "tomorrow 14:00")',
      },
      { kind: "result", text: "3 free slots → 14:00, 14:30, 15:15" },
    ],
  },
  { who: "user", text: "14:30 please" },
  {
    who: "bot",
    text: "Booked! ✅ Haircut tomorrow at 14:30 (60 min). You'll get a reminder beforehand.",
    trace: [
      {
        kind: "tool",
        text: 'book(service: "Haircut", start: "tomorrow 14:30")',
      },
    ],
  },
];

function TraceTag({ kind }: { kind: string }) {
  const tone =
    kind === "tool"
      ? "bg-accent-soft text-accent"
      : kind === "result"
        ? "bg-success-soft text-success"
        : "bg-surface-3 text-muted";
  return (
    <span
      className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${tone}`}
    >
      {kind}
    </span>
  );
}

function Demo() {
  return (
    <Section id="demo">
      <div className="mx-auto mb-7 max-w-2xl text-center">
        <div className="mb-2.5 text-[13px] font-bold uppercase tracking-wider text-pink">
          See how it works
        </div>
        <Heading>Talk to a real assistant</Heading>
        <p className="mx-auto mt-3 max-w-lg text-base leading-relaxed text-muted">
          This is <strong className="text-ink">Ana Studio</strong> — a demo
          salon with a live schedule. Ask for a time and actually book;
          you&apos;ll see every step the agent takes.
        </p>
      </div>

      <div className="mx-auto max-w-xl overflow-hidden rounded-[22px] border border-line bg-surface shadow-pop">
        <div className="flex items-center gap-3 border-b border-line bg-surface-2 px-4 py-3.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-[11px] bg-pink text-base font-extrabold text-accent-contrast">
            A
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold">Ana Studio</div>
            <div className="text-xs text-faint">
              Haircut · demo schedule · always bookable
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-success-soft px-2.5 py-1 text-xs font-bold text-success">
            <span className="h-1.5 w-1.5 rounded-full bg-current" /> Online
          </span>
        </div>

        <div className="flex flex-col gap-3.5 p-4">
          {SAMPLE.map((m, i) =>
            m.who === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] rounded-[16px_16px_4px_16px] bg-accent px-3.5 py-2.5 text-sm leading-relaxed text-accent-contrast">
                  {m.text}
                </div>
              </div>
            ) : (
              <div key={i} className="flex flex-col gap-2">
                {m.trace && (
                  <div className="max-w-[90%] rounded-xl border border-dashed border-line-strong bg-surface-2 p-3">
                    <div className="mb-1.5 flex items-center gap-1.5 text-[10.5px] font-extrabold uppercase tracking-wider text-faint">
                      <SparkIcon /> Agent steps
                    </div>
                    <div className="flex flex-col gap-1.5">
                      {m.trace.map((t, j) => (
                        <div
                          key={j}
                          className="flex items-start gap-2 text-xs leading-snug"
                        >
                          <TraceTag kind={t.kind} />
                          <span className="font-mono text-[11.5px] text-muted">
                            {t.text}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="max-w-[90%] rounded-[16px_16px_16px_4px] bg-surface-3 px-3.5 py-2.5 text-sm leading-relaxed">
                  {m.text}
                </div>
              </div>
            ),
          )}
        </div>

        <div className="border-t border-line bg-surface-2 p-4 text-center">
          <a href={APP_URL} className={`${primaryBtn} w-full justify-center`}>
            Start free to try it yourself <ArrowIcon />
          </a>
        </div>
      </div>
    </Section>
  );
}

/* ---------- how it works ---------- */

const STEPS = [
  {
    num: "1",
    icon: <SettingsIcon />,
    title: "Sign up & describe your business",
    body: "Add your services, hours, and FAQ — or self-host the open source if you'd rather.",
  },
  {
    num: "2",
    icon: <MessageIcon />,
    title: "Connect your Telegram bot",
    body: "Paste one bot token. That's the whole setup — no servers, no code.",
  },
  {
    num: "3",
    icon: <SparkIcon />,
    title: "Customers message your bot",
    body: "Tovayo answers, books, reschedules, and reminds — in your customer's language.",
  },
];

function HowItWorks() {
  return (
    <Section id="how">
      <div className="mb-9 text-center">
        <Heading>Live in three steps</Heading>
      </div>
      <div className="mx-auto grid max-w-4xl gap-4 md:grid-cols-3">
        {STEPS.map((s) => (
          <div
            key={s.num}
            className="relative rounded-[18px] border border-line bg-surface p-6 shadow-card"
          >
            <div className="absolute right-5 top-5 text-4xl font-extrabold leading-none text-surface-3">
              {s.num}
            </div>
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-[13px] bg-accent-soft text-accent">
              {s.icon}
            </div>
            <h3 className="mb-1.5 text-[17px] font-extrabold">{s.title}</h3>
            <p className="text-sm leading-relaxed text-muted">{s.body}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ---------- features ---------- */

const FEATURES = [
  {
    icon: <MessageIcon />,
    title: "Answers from your info",
    body: "Replies from your own services, prices, hours, and FAQ — never makes things up.",
  },
  {
    icon: <CalendarIcon />,
    title: "Books for real",
    body: "Books, reschedules, and cancels real appointments, with double-booking protection.",
  },
  {
    icon: <ClipboardIcon />,
    title: "Collects what you need",
    body: "Asks for the details you require before booking — e.g. a birth date for an astrologer.",
  },
  {
    icon: <BellIcon />,
    title: "Cuts no-shows",
    body: "Sends reminders before each appointment so customers actually show up.",
  },
  {
    icon: <HandIcon />,
    title: "You can take over",
    body: "Jump into any chat and reply as yourself; the AI steps aside until you hand it back.",
  },
  {
    icon: <GlobeIcon />,
    title: "Four languages",
    body: "English, Spanish, Russian, and Chinese — in the customer's own language, out of the box.",
  },
];

function Features() {
  return (
    <Section id="features">
      <div className="mb-9 text-center">
        <Heading>Everything a front desk does</Heading>
        <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-muted">
          Without the clunky CRM, the missed messages, or the monthly bill.
        </p>
      </div>
      <div className="mx-auto grid max-w-4xl gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f) => (
          <div
            key={f.title}
            className="rounded-[16px] border border-line bg-surface p-5 shadow-card"
          >
            <div className="mb-3.5 flex h-10 w-10 items-center justify-center rounded-xl bg-pink-soft text-pink">
              {f.icon}
            </div>
            <h3 className="mb-1.5 text-[15.5px] font-extrabold">{f.title}</h3>
            <p className="text-sm leading-relaxed text-muted">{f.body}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ---------- two ways to run it ---------- */

const OSS_POINTS = [
  "Your servers, your data",
  "MIT — commercial use OK",
  "Change anything",
  "No limits, ever",
];
const HOSTED_POINTS = [
  "Zero setup",
  "We run & update it",
  "Free & unlimited",
  "Delete your data anytime",
];

function RunCard({
  title,
  sub,
  body,
  points,
  cta,
  href,
  highlight = false,
}: {
  title: string;
  sub: string;
  body: string;
  points: string[];
  cta: string;
  href: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-[20px] border bg-surface p-7 shadow-card ${
        highlight ? "border-accent" : "border-line-strong"
      }`}
    >
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-[11px] bg-surface-3 text-ink">
          {highlight ? <SparkIcon /> : <CodeIcon />}
        </div>
        <div>
          <div className="text-lg font-extrabold">{title}</div>
          <div className="text-xs font-bold text-success">{sub}</div>
        </div>
      </div>
      <p className="mb-4 text-sm leading-relaxed text-muted">{body}</p>
      <div className="mb-6 flex flex-col gap-2.5">
        {points.map((p) => (
          <div key={p} className="flex items-center gap-2.5 text-sm">
            <span className="flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full bg-success-soft text-success">
              <CheckIcon />
            </span>
            {p}
          </div>
        ))}
      </div>
      <a
        href={href}
        className={
          highlight
            ? `${primaryBtn} w-full justify-center`
            : `${secondaryBtn} w-full justify-center`
        }
      >
        {cta}
      </a>
    </div>
  );
}

function RunItTwoWays() {
  return (
    <Section>
      <div className="mb-9 text-center">
        <Heading>Two ways to run it. Both free.</Heading>
        <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-muted">
          Not &quot;free vs paid&quot; — equal first-class options. Pick what
          fits.
        </p>
      </div>
      <div className="mx-auto grid max-w-3xl gap-4 md:grid-cols-2">
        <RunCard
          title="Self-host"
          sub="Free forever"
          body="Take the code, run it on your servers, change anything. MIT license — commercial use allowed."
          points={OSS_POINTS}
          cta="View on GitHub"
          href={GITHUB_URL}
        />
        <RunCard
          title="Hosted at tovayo.com"
          sub="Free & unlimited"
          body="Zero setup — we run it for you. Connect your bot and go. Your data, deletable anytime."
          points={HOSTED_POINTS}
          cta="Start free"
          href={APP_URL}
          highlight
        />
      </div>
    </Section>
  );
}

/* ---------- trust & data ---------- */

function TrustAndData() {
  return (
    <Section>
      <div className="mx-auto max-w-2xl rounded-[20px] border border-line bg-surface p-7 text-center shadow-card">
        <Heading>Honest about your data</Heading>
        <p className="mx-auto mt-3 max-w-lg text-base leading-relaxed text-muted">
          Conversations are stored on our servers so the assistant has context.
          You can delete your account and{" "}
          <strong className="text-ink">all</strong> of your data at any time —
          instantly and irreversibly.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-3 text-sm font-semibold">
          <a href="/privacy" className="text-accent hover:underline">
            Privacy Policy
          </a>
          <span className="text-faint">·</span>
          <a href="/terms" className="text-accent hover:underline">
            Terms of Service
          </a>
        </div>
      </div>
    </Section>
  );
}

/* ---------- faq ---------- */

const FAQ = [
  [
    "Is it really free?",
    "Yes. The hosted service at tovayo.com is free and unlimited, no card required. The code is MIT-licensed, so self-hosting is free too.",
  ],
  [
    "Can I use it for my business commercially?",
    "Absolutely. The MIT license lets you use, modify, and run the code for any purpose, including commercially. The hosted service is for running your real business.",
  ],
  [
    "Where is my data?",
    "On our servers (for the hosted service), or your own if you self-host. We don't sell it or train models on your conversations.",
  ],
  [
    "Can I delete everything?",
    "Yes — Settings → Danger zone → Delete account permanently erases your business and all its data, with no undo.",
  ],
  ["Which channels are supported?", "Telegram today. WhatsApp is planned."],
  [
    "Do I need to know how to code?",
    "No, for the hosted service — you just connect a bot token. Self-hosting needs some technical setup.",
  ],
];

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-line">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-4 py-4 text-left text-[15px] font-bold"
      >
        {q}
        <span
          className={`shrink-0 text-muted transition ${open ? "rotate-45" : ""}`}
        >
          <PlusIcon />
        </span>
      </button>
      {open && <p className="pb-4 text-sm leading-relaxed text-muted">{a}</p>}
    </div>
  );
}

function Faq() {
  return (
    <Section id="faq">
      <div className="mb-7 text-center">
        <Heading>Questions, answered</Heading>
      </div>
      <div className="mx-auto max-w-2xl">
        {FAQ.map(([q, a]) => (
          <FaqItem key={q} q={q} a={a} />
        ))}
      </div>
    </Section>
  );
}

/* ---------- cta banner ---------- */

function CtaBanner() {
  return (
    <Section>
      <div className="relative overflow-hidden rounded-[24px] border border-line bg-surface px-6 py-12 text-center shadow-pop">
        <div className="pointer-events-none absolute left-1/2 top-[-80px] h-[300px] w-[600px] max-w-full -translate-x-1/2 rounded-full bg-accent-soft opacity-70 blur-2xl" />
        <div className="relative">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Your front desk, handled.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-muted">
            Free, unlimited, and open source. Set it up in minutes.
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <a href={APP_URL} className={primaryBtn}>
              Start free <ArrowIcon />
            </a>
            <a href={GITHUB_URL} className={secondaryBtn}>
              <GithubIcon /> View on GitHub
            </a>
          </div>
        </div>
      </div>
    </Section>
  );
}

/* ---------- footer ---------- */

function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 sm:flex-row sm:px-8">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-sm font-extrabold text-accent-contrast">
            T
          </span>
          <span className="text-sm font-bold text-muted">
            Tovayo — open-source AI front desk.
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-sm font-semibold text-muted">
          <a href={GITHUB_URL} className="hover:text-ink">
            GitHub
          </a>
          <a href="/terms" className="hover:text-ink">
            Terms
          </a>
          <a href="/privacy" className="hover:text-ink">
            Privacy
          </a>
          <a href={APP_URL} className="hover:text-ink">
            Start free
          </a>
        </div>
      </div>
    </footer>
  );
}
