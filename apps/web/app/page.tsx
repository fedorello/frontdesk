"use client";

import { useEffect, useState } from "react";

import { I18nProvider, useI18n } from "@/app/lib/i18n";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

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

const STEP_ICONS = [
  <SettingsIcon key="0" />,
  <MessageIcon key="1" />,
  <SparkIcon key="2" />,
];
const FEATURE_ICONS = [
  <MessageIcon key="0" />,
  <CalendarIcon key="1" />,
  <ClipboardIcon key="2" />,
  <BellIcon key="3" />,
  <HandIcon key="4" />,
  <GlobeIcon key="5" />,
];

/* ---------- page ---------- */

export default function Landing() {
  return (
    <I18nProvider>
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
    </I18nProvider>
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
  const { c } = useI18n();
  const [dark, toggle] = useTheme();
  const links: [string, string][] = [
    [c.nav.demo, "#demo"],
    [c.nav.how, "#how"],
    [c.nav.features, "#features"],
    [c.nav.faq, "#faq"],
  ];
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
          {links.map(([label, href]) => (
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
          <LanguageSwitcher />
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
            {c.nav.github}
          </a>
          <a
            href={APP_URL}
            className="rounded-[10px] bg-accent px-4 py-2 text-sm font-bold text-accent-contrast"
          >
            {c.nav.start}
          </a>
        </div>
      </div>
    </nav>
  );
}

/* ---------- hero ---------- */

function Hero() {
  const { c } = useI18n();
  return (
    <header id="top" className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-1/2 top-[-120px] h-[460px] w-[760px] max-w-full -translate-x-1/2 rounded-full bg-accent-soft opacity-80 blur-2xl" />
      <Section className="relative text-center">
        <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-[13px] font-semibold text-muted shadow-card">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          {c.hero.badge}
        </span>
        <h1 className="mx-auto max-w-3xl text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">
          {c.hero.title1}
          <span className="text-accent">{c.hero.titleAccent}</span>
          {c.hero.title2}
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-muted">
          {c.hero.sub}
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <a href={APP_URL} className={primaryBtn}>
            {c.hero.ctaPrimary} <ArrowIcon />
          </a>
          <a href={GITHUB_URL} className={secondaryBtn}>
            <GithubIcon /> {c.hero.ctaSecondary}
          </a>
        </div>
        <p className="mt-5 text-[13.5px] font-semibold text-faint">
          {c.hero.trust}
        </p>
      </Section>
    </header>
  );
}

/* ---------- demo ---------- */

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
  const { c } = useI18n();
  return (
    <Section id="demo">
      <div className="mx-auto mb-7 max-w-2xl text-center">
        <div className="mb-2.5 text-[13px] font-bold uppercase tracking-wider text-pink">
          {c.demo.eyebrow}
        </div>
        <Heading>{c.demo.title}</Heading>
        <p className="mx-auto mt-3 max-w-lg text-base leading-relaxed text-muted">
          {c.demo.subA}
          <strong className="text-ink">Ana Studio</strong>
          {c.demo.subB}
        </p>
      </div>

      <div className="mx-auto max-w-xl overflow-hidden rounded-[22px] border border-line bg-surface shadow-pop">
        <div className="flex items-center gap-3 border-b border-line bg-surface-2 px-4 py-3.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-[11px] bg-pink text-base font-extrabold text-accent-contrast">
            A
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold">Ana Studio</div>
            <div className="text-xs text-faint">{c.demo.headerSub}</div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-success-soft px-2.5 py-1 text-xs font-bold text-success">
            <span className="h-1.5 w-1.5 rounded-full bg-current" />{" "}
            {c.demo.online}
          </span>
        </div>

        <div className="flex flex-col gap-3.5 p-4">
          {c.demo.sample.map((m, i) =>
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
                      <SparkIcon /> {c.demo.agentSteps}
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
            {c.demo.cta} <ArrowIcon />
          </a>
        </div>
      </div>
    </Section>
  );
}

/* ---------- how it works ---------- */

function HowItWorks() {
  const { c } = useI18n();
  return (
    <Section id="how">
      <div className="mb-9 text-center">
        <Heading>{c.how.title}</Heading>
      </div>
      <div className="mx-auto grid max-w-4xl gap-4 md:grid-cols-3">
        {c.how.steps.map((s, i) => (
          <div
            key={i}
            className="relative rounded-[18px] border border-line bg-surface p-6 shadow-card"
          >
            <div className="absolute right-5 top-5 text-4xl font-extrabold leading-none text-surface-3">
              {i + 1}
            </div>
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-[13px] bg-accent-soft text-accent">
              {STEP_ICONS[i]}
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

function Features() {
  const { c } = useI18n();
  return (
    <Section id="features">
      <div className="mb-9 text-center">
        <Heading>{c.features.title}</Heading>
        <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-muted">
          {c.features.sub}
        </p>
      </div>
      <div className="mx-auto grid max-w-4xl gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {c.features.items.map((f, i) => (
          <div
            key={i}
            className="rounded-[16px] border border-line bg-surface p-5 shadow-card"
          >
            <div className="mb-3.5 flex h-10 w-10 items-center justify-center rounded-xl bg-pink-soft text-pink">
              {FEATURE_ICONS[i]}
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

function RunCard({
  name,
  tag,
  body,
  points,
  cta,
  href,
  highlight = false,
}: {
  name: string;
  tag: string;
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
          <div className="text-lg font-extrabold">{name}</div>
          <div className="text-xs font-bold text-success">{tag}</div>
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
  const { c } = useI18n();
  return (
    <Section>
      <div className="mb-9 text-center">
        <Heading>{c.run.title}</Heading>
        <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-muted">
          {c.run.sub}
        </p>
      </div>
      <div className="mx-auto grid max-w-3xl gap-4 md:grid-cols-2">
        <RunCard {...c.run.selfHost} href={GITHUB_URL} />
        <RunCard {...c.run.hosted} href={APP_URL} highlight />
      </div>
    </Section>
  );
}

/* ---------- trust & data ---------- */

function TrustAndData() {
  const { c } = useI18n();
  return (
    <Section>
      <div className="mx-auto max-w-2xl rounded-[20px] border border-line bg-surface p-7 text-center shadow-card">
        <Heading>{c.trust.title}</Heading>
        <p className="mx-auto mt-3 max-w-lg text-base leading-relaxed text-muted">
          {c.trust.body}
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-3 text-sm font-semibold">
          <a href="/privacy" className="text-accent hover:underline">
            {c.trust.privacy}
          </a>
          <span className="text-faint">·</span>
          <a href="/terms" className="text-accent hover:underline">
            {c.trust.terms}
          </a>
        </div>
      </div>
    </Section>
  );
}

/* ---------- faq ---------- */

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
  const { c } = useI18n();
  return (
    <Section id="faq">
      <div className="mb-7 text-center">
        <Heading>{c.faq.title}</Heading>
      </div>
      <div className="mx-auto max-w-2xl">
        {c.faq.items.map(([q, a]) => (
          <FaqItem key={q} q={q} a={a} />
        ))}
      </div>
    </Section>
  );
}

/* ---------- cta banner ---------- */

function CtaBanner() {
  const { c } = useI18n();
  return (
    <Section>
      <div className="relative overflow-hidden rounded-[24px] border border-line bg-surface px-6 py-12 text-center shadow-pop">
        <div className="pointer-events-none absolute left-1/2 top-[-80px] h-[300px] w-[600px] max-w-full -translate-x-1/2 rounded-full bg-accent-soft opacity-70 blur-2xl" />
        <div className="relative">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            {c.cta.title}
          </h2>
          <p className="mx-auto mt-3 max-w-md text-base leading-relaxed text-muted">
            {c.cta.sub}
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <a href={APP_URL} className={primaryBtn}>
              {c.hero.ctaPrimary} <ArrowIcon />
            </a>
            <a href={GITHUB_URL} className={secondaryBtn}>
              <GithubIcon /> {c.hero.ctaSecondary}
            </a>
          </div>
        </div>
      </div>
    </Section>
  );
}

/* ---------- footer ---------- */

function Footer() {
  const { c } = useI18n();
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 sm:flex-row sm:px-8">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-sm font-extrabold text-accent-contrast">
            T
          </span>
          <span className="text-sm font-bold text-muted">{c.footer.brand}</span>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-sm font-semibold text-muted">
          <a href={GITHUB_URL} className="hover:text-ink">
            {c.footer.github}
          </a>
          <a href="/terms" className="hover:text-ink">
            {c.footer.terms}
          </a>
          <a href="/privacy" className="hover:text-ink">
            {c.footer.privacy}
          </a>
          <a href={APP_URL} className="hover:text-ink">
            {c.footer.start}
          </a>
        </div>
      </div>
    </footer>
  );
}
