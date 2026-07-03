"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { writeCookie } from "@/app/lib/cookie";
import { I18nProvider, useI18n } from "@/app/lib/i18n";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Logo } from "@/components/Logo";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://app.tovayo.com";

/* ---------- content (owner guide, Telegram only) ---------- */

type Step = { title: string; body: string; note?: string };
type Guide = {
  openApp: string;
  home: string;
  badge: string;
  title: string;
  sub: string;
  intro: string;
  stepsTitle: string;
  steps: Step[];
  doesTitle: string;
  does: string[];
  whereTitle: string;
  where: string;
  faqTitle: string;
  faq: { q: string; a: string }[];
  outroTitle: string;
  outro: string;
  outroCta: string;
  privacy: string;
  terms: string;
  back: string;
};

const RU: Guide = {
  openApp: "Открыть приложение",
  home: "На главную",
  badge: "Руководство",
  title: "Как пользоваться Tovayo",
  sub: "Пошагово: от регистрации до работающего Telegram-бота, который сам отвечает клиентам и записывает их. Занимает около 10 минут.",
  intro:
    "Tovayo — это ИИ-ресепшионист. Он отвечает на сообщения клиентов в Telegram, записывает их в ваш календарь и напоминает о визите — чтобы вы не теряли клиентов и не отвлекались на переписку.",
  stepsTitle: "7 шагов",
  steps: [
    {
      title: "Заведите аккаунт",
      body: "Откройте app.tovayo.com и нажмите «Начать бесплатно». Войти можно через Google или по email и паролю. Укажите название бизнеса и часовой пояс.",
    },
    {
      title: "Заполните профиль бизнеса",
      body: "Настройки → Профиль бизнеса: название, короткое описание, часовой пояс и адрес. Если работаете онлайн — включите «Онлайн», и адрес скроется.",
    },
    {
      title: "Укажите часы работы",
      body: "Настройки → Группы. Задайте рабочие часы по дням недели. По умолчанию уже стоит пн–пт, 9:00–17:00 — просто поправьте под себя.",
    },
    {
      title: "Добавьте услуги",
      body: "Настройки → Услуги. Для каждой услуги: название, длительность, цена и за сколько дней вперёд можно записаться. Можно добавить до 5 вопросов, которые бот задаст перед записью (например, имя или дату рождения), и указать формат ответа.",
      note: "Хотите подтверждать записи вручную? Включите «Требует вашего подтверждения» — тогда запись подождёт вашего ОК в разделе «Заявки».",
    },
    {
      title: "Создайте бота в Telegram",
      body: "В Telegram откройте @BotFather, отправьте команду /newbot и придумайте имя. В ответ придёт токен — длинная строка вида 123456:ABC…. Скопируйте её.",
    },
    {
      title: "Подключите бота к Tovayo",
      body: "В Tovayo: Настройки → «Подключить Telegram». Вставьте токен и нажмите «Подключить». Статус сменится на «Подключён как @вашбот» — значит всё готово.",
    },
    {
      title: "Проверьте",
      body: "Откройте своего бота в Telegram и напишите ему как клиент: «Здравствуйте, можно записаться?». ИИ ответит, предложит свободное время и запишет. Готово!",
      note: "Бонус: хотите получать уведомления о новых записях? Откройте бота, отправьте /connect и перейдите по ссылке (будучи залогинены в Tovayo).",
    },
  ],
  doesTitle: "Что бот делает сам",
  does: [
    "Отвечает на вопросы: часы, цены, услуги, адрес.",
    "Проверяет свободное время и записывает в ваш календарь.",
    "Задаёт ваши вопросы перед записью.",
    "Напоминает клиенту о визите — меньше неявок.",
    "Отвечает на языке клиента автоматически.",
    "Передаёт вам, когда не может помочь сам; возвраты денег — только с вашим подтверждением.",
  ],
  whereTitle: "Где всё видно",
  where:
    "Записи — в разделе «Календарь». Переписки с клиентами — в «Разговоры». Записи, ждущие подтверждения, — в «Заявки».",
  faqTitle: "Частые вопросы",
  faq: [
    {
      q: "Нужен свой сервер или номер телефона?",
      a: "Нет. Всё работает в облаке. Нужен только бот из @BotFather — это бесплатно и занимает минуту.",
    },
    {
      q: "Сколько это стоит?",
      a: "Бесплатно, карта не нужна.",
    },
    {
      q: "На каких языках говорит бот?",
      a: "На языке клиента, автоматически. Интерфейс — русский, английский, испанский и китайский.",
    },
    {
      q: "А если клиент задаст сложный вопрос?",
      a: "Бот честно передаст его вам, а не выдумает ответ.",
    },
  ],
  outroTitle: "Готовы попробовать?",
  outro: "Настройка занимает пару минут, а бот работает круглосуточно.",
  outroCta: "Начать бесплатно",
  privacy: "Конфиденциальность",
  terms: "Условия",
  back: "← tovayo.com",
};

const EN: Guide = {
  openApp: "Open app",
  home: "Home",
  badge: "Guide",
  title: "How to use Tovayo",
  sub: "Step by step: from signing up to a working Telegram bot that answers your customers and books them in. Takes about 10 minutes.",
  intro:
    "Tovayo is an AI receptionist. It answers your customers on Telegram, books them into your calendar, and reminds them before the visit — so you never lose a customer or get stuck replying to messages.",
  stepsTitle: "7 steps",
  steps: [
    {
      title: "Create an account",
      body: "Open app.tovayo.com and click “Start free”. Sign in with Google or with an email and password. Enter your business name and time zone.",
    },
    {
      title: "Fill in your business profile",
      body: "Settings → Business profile: name, a short description, time zone and address. If you work online, turn on “Online” and the address is hidden.",
    },
    {
      title: "Set your working hours",
      body: "Settings → Groups. Set working hours per weekday. It starts with Mon–Fri, 9:00–17:00 — just adjust it to fit you.",
    },
    {
      title: "Add your services",
      body: "Settings → Services. For each service: name, duration, price and how many days ahead people can book. You can add up to 5 questions the bot asks before booking (e.g. name or birth date) and set the answer format.",
      note: "Want to confirm bookings by hand? Turn on “Requires your confirmation” — the booking then waits for your OK in the Approvals section.",
    },
    {
      title: "Create a bot in Telegram",
      body: "In Telegram open @BotFather, send /newbot and pick a name. You’ll get a token — a long string like 123456:ABC…. Copy it.",
    },
    {
      title: "Connect the bot to Tovayo",
      body: "In Tovayo: Settings → “Connect Telegram”. Paste the token and click “Connect”. The status changes to “Connected as @yourbot” — you’re done.",
    },
    {
      title: "Test it",
      body: "Open your bot in Telegram and message it like a customer: “Hi, can I book an appointment?”. The AI replies, offers open times and books it. Done!",
      note: "Bonus: want alerts for new bookings? Open the bot, send /connect and follow the link it replies with (while signed in to Tovayo).",
    },
  ],
  doesTitle: "What the bot does on its own",
  does: [
    "Answers questions: hours, prices, services, location.",
    "Checks open times and books into your calendar.",
    "Asks your intake questions before booking.",
    "Reminds the customer before the visit — fewer no-shows.",
    "Replies in the customer’s language automatically.",
    "Hands off to you when it can’t help; refunds happen only with your approval.",
  ],
  whereTitle: "Where to see everything",
  where:
    "Bookings live in Calendar. Customer chats are in Conversations. Bookings waiting for your OK are in Approvals.",
  faqTitle: "Common questions",
  faq: [
    {
      q: "Do I need my own server or phone number?",
      a: "No. Everything runs in the cloud. You only need a bot from @BotFather — it’s free and takes a minute.",
    },
    {
      q: "How much does it cost?",
      a: "Free, no card required.",
    },
    {
      q: "What languages does the bot speak?",
      a: "The customer’s language, automatically. The dashboard is in English, Spanish, Russian and Chinese.",
    },
    {
      q: "What if a customer asks something hard?",
      a: "The bot honestly hands it to you instead of making up an answer.",
    },
  ],
  outroTitle: "Ready to try?",
  outro: "Setup takes a couple of minutes, and the bot works around the clock.",
  outroCta: "Start free",
  privacy: "Privacy",
  terms: "Terms",
  back: "← tovayo.com",
};

/* ---------- small chrome ---------- */

function useTheme(): [boolean, () => void] {
  const [dark, setDark] = useState(true);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync to the no-flash theme on mount
    setDark(document.documentElement.getAttribute("data-theme") === "dark");
  }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
    writeCookie("tovayo.theme", next ? "dark" : "light"); // shared with the app
  };
  return [dark, toggle];
}

const Sun = () => (
  <svg width={17} height={17} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="4.5" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" />
  </svg>
);
const Moon = () => (
  <svg width={17} height={17} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5Z" />
  </svg>
);

const primaryBtn =
  "inline-flex items-center gap-2 rounded-xl bg-accent px-6 py-3.5 text-base font-bold text-accent-contrast shadow-card transition hover:opacity-90";

/* ---------- page ---------- */

function GuidePage() {
  const { locale } = useI18n();
  const g = locale === "ru" ? RU : EN; // guide ships in RU + EN; other UI languages see EN

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <nav className="sticky top-0 z-40 border-b border-line bg-surface/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-4xl items-center gap-4 px-5 py-3 sm:px-8">
          <Link href="/" className="flex items-center gap-2" aria-label={g.home}>
            <Logo size={28} />
            <span className="text-lg font-extrabold tracking-tight">tovayo</span>
          </Link>
          <div className="ml-auto flex items-center gap-2">
            <LanguageSwitcher />
            <ThemeToggle />
            <a href={APP_URL} className="hidden rounded-lg bg-accent px-4 py-2 text-sm font-bold text-accent-contrast transition hover:opacity-90 sm:inline-flex">
              {g.openApp}
            </a>
          </div>
        </div>
      </nav>

      <div className="mx-auto w-full max-w-2xl px-5 pb-24 pt-14 sm:px-8">
        {/* hero */}
        <span className="inline-block rounded-full border border-line-strong bg-surface px-3 py-1 text-xs font-semibold uppercase tracking-wide text-muted">
          {g.badge}
        </span>
        <h1 className="mt-4 text-4xl font-extrabold leading-[1.1] tracking-tight sm:text-5xl">
          {g.title}
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-muted">{g.sub}</p>
        <p className="mt-4 leading-relaxed text-ink/90">{g.intro}</p>

        {/* steps */}
        <h2 className="mt-14 text-2xl font-extrabold tracking-tight">{g.stepsTitle}</h2>
        <ol className="mt-6 space-y-4">
          {g.steps.map((step, i) => (
            <li
              key={i}
              className="flex gap-4 rounded-2xl border border-line bg-surface p-5 shadow-card"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-base font-extrabold text-accent-contrast">
                {i + 1}
              </span>
              <div>
                <h3 className="text-lg font-bold">{step.title}</h3>
                <p className="mt-1.5 leading-relaxed text-muted">{step.body}</p>
                {step.note && (
                  <p className="mt-3 rounded-lg border border-dashed border-line-strong bg-surface-2 px-3.5 py-2.5 text-sm leading-relaxed text-ink/80">
                    {step.note}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>

        {/* what it does */}
        <h2 className="mt-14 text-2xl font-extrabold tracking-tight">{g.doesTitle}</h2>
        <ul className="mt-5 space-y-2.5">
          {g.does.map((item, i) => (
            <li key={i} className="flex gap-3 leading-relaxed">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <span className="text-ink/90">{item}</span>
            </li>
          ))}
        </ul>

        {/* where */}
        <h2 className="mt-14 text-2xl font-extrabold tracking-tight">{g.whereTitle}</h2>
        <p className="mt-4 leading-relaxed text-muted">{g.where}</p>

        {/* faq */}
        <h2 className="mt-14 text-2xl font-extrabold tracking-tight">{g.faqTitle}</h2>
        <div className="mt-5 space-y-3">
          {g.faq.map((item, i) => (
            <div key={i} className="rounded-2xl border border-line bg-surface p-5">
              <p className="font-bold">{item.q}</p>
              <p className="mt-1.5 leading-relaxed text-muted">{item.a}</p>
            </div>
          ))}
        </div>

        {/* outro */}
        <div className="mt-16 rounded-2xl border border-line-strong bg-surface p-8 text-center shadow-card">
          <h2 className="text-2xl font-extrabold tracking-tight">{g.outroTitle}</h2>
          <p className="mx-auto mt-3 max-w-md leading-relaxed text-muted">{g.outro}</p>
          <a href={APP_URL} className={`${primaryBtn} mt-6`}>
            {g.outroCta}
          </a>
        </div>

        {/* footer */}
        <footer className="mt-14 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted">
          <Link href="/" className="hover:text-ink">
            {g.back}
          </Link>
          <a href="/privacy" className="hover:text-ink">
            {g.privacy}
          </a>
          <a href="/terms" className="hover:text-ink">
            {g.terms}
          </a>
        </footer>
      </div>
    </main>
  );
}

function ThemeToggle() {
  const [dark, toggle] = useTheme();
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Toggle theme"
      className="flex h-9 w-9 items-center justify-center rounded-lg border border-line-strong bg-surface text-ink transition hover:bg-surface-3"
    >
      {dark ? <Sun /> : <Moon />}
    </button>
  );
}

export default function Page() {
  return (
    <I18nProvider>
      <GuidePage />
    </I18nProvider>
  );
}
