"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { readLocaleCookie, writeLocaleCookie } from "./localeCookie";

export const LOCALES = ["en", "es", "ru", "zh"] as const;
export type Locale = (typeof LOCALES)[number];
export const LOCALE_NAMES: Record<Locale, string> = {
  en: "English",
  es: "Español",
  ru: "Русский",
  zh: "中文",
};

type Sample = {
  who: "user" | "bot";
  text: string;
  trace?: { kind: string; text: string }[];
};

interface Copy {
  nav: {
    demo: string;
    how: string;
    features: string;
    faq: string;
    github: string;
    start: string;
  };
  hero: {
    badge: string;
    title1: string;
    titleAccent: string;
    title2: string;
    sub: string;
    ctaPrimary: string;
    ctaSecondary: string;
    trust: string;
  };
  demo: {
    eyebrow: string;
    title: string;
    subA: string;
    subB: string;
    headerSub: string;
    online: string;
    agentSteps: string;
    cta: string;
    sample: Sample[];
  };
  how: { title: string; steps: { title: string; body: string }[] };
  features: {
    title: string;
    sub: string;
    items: { title: string; body: string }[];
  };
  run: {
    title: string;
    sub: string;
    selfHost: {
      name: string;
      tag: string;
      body: string;
      points: string[];
      cta: string;
    };
    hosted: {
      name: string;
      tag: string;
      body: string;
      points: string[];
      cta: string;
    };
  };
  trust: { title: string; body: string; privacy: string; terms: string };
  faq: { title: string; items: [string, string][] };
  name: {
    eyebrow: string;
    title: string;
    intro: string;
    words: { word: string; lang: string; meaning: string }[];
    punchline: string;
  };
  cta: { title: string; sub: string };
  voice: {
    title: string;
    sub: string;
    pricing: string;
    comingSoon: string;
    signInCta: string;
    signInNote: string;
    callPrompt: string;
    error: string;
  };
  footer: {
    brand: string;
    github: string;
    terms: string;
    privacy: string;
    start: string;
  };
}

const en: Copy = {
  nav: {
    demo: "Demo",
    how: "How it works",
    features: "Features",
    faq: "FAQ",
    github: "View on GitHub",
    start: "Start free",
  },
  hero: {
    badge: "Free & open source · MIT",
    title1: "A free ",
    titleAccent: "AI front desk",
    title2: " for your small business",
    sub: "It answers customers, books appointments, and sends reminders — 24/7, in their language. Use the open source, or let us host it for you. Both free.",
    ctaPrimary: "Start free",
    ctaSecondary: "View on GitHub",
    trust: "Free & unlimited · Open source · No card required",
  },
  demo: {
    eyebrow: "See how it works",
    title: "Talk to a real assistant",
    subA: "This is ",
    subB: " — a demo salon with a live schedule. Ask for a time and actually book; you'll see every step the agent takes.",
    headerSub: "Haircut · demo schedule · always bookable",
    online: "Online",
    agentSteps: "Agent steps",
    cta: "Start free to try it yourself",
    sample: [
      { who: "user", text: "Hi! Can I get a haircut tomorrow afternoon?" },
      {
        who: "bot",
        text: "Of course! Tomorrow afternoon I have 14:00, 14:30 and 15:15 open. Which works?",
        trace: [
          { kind: "think", text: "Customer wants a haircut tomorrow PM" },
          {
            kind: "tool",
            text: 'find_availability(service: "Haircut", around: "tomorrow 14:00")',
          },
          { kind: "result", text: "3 free slots -> 14:00, 14:30, 15:15" },
        ],
      },
      { who: "user", text: "14:30 please" },
      {
        who: "bot",
        text: "Booked! Haircut tomorrow at 14:30 (60 min). You'll get a reminder beforehand.",
        trace: [
          {
            kind: "tool",
            text: 'book(service: "Haircut", start: "tomorrow 14:30")',
          },
        ],
      },
    ],
  },
  how: {
    title: "Live in three steps",
    steps: [
      {
        title: "Sign up & describe your business",
        body: "Add your services, hours, and FAQ — or self-host the open source if you'd rather.",
      },
      {
        title: "Connect your Telegram bot",
        body: "Paste one bot token. That's the whole setup — no servers, no code.",
      },
      {
        title: "Customers message your bot",
        body: "Tovayo answers, books, reschedules, and reminds — in your customer's language.",
      },
    ],
  },
  features: {
    title: "Everything a front desk does",
    sub: "Without the clunky CRM, the missed messages, or the monthly bill.",
    items: [
      {
        title: "Answers from your info",
        body: "Replies from your own services, prices, hours, and FAQ — never makes things up.",
      },
      {
        title: "Books for real",
        body: "Books, reschedules, and cancels real appointments, with double-booking protection.",
      },
      {
        title: "Collects what you need",
        body: "Asks for the details you require before booking — e.g. a birth date for an astrologer.",
      },
      {
        title: "Cuts no-shows",
        body: "Sends reminders before each appointment so customers actually show up.",
      },
      {
        title: "You can take over",
        body: "Jump into any chat and reply as yourself; the AI steps aside until you hand it back.",
      },
      {
        title: "Four languages",
        body: "English, Spanish, Russian, and Chinese — in the customer's own language, out of the box.",
      },
    ],
  },
  run: {
    title: "Two ways to run it. Both free.",
    sub: 'Not "free vs paid" — equal first-class options. Pick what fits.',
    selfHost: {
      name: "Self-host",
      tag: "Free forever",
      body: "Take the code, run it on your servers, change anything. MIT license — commercial use allowed.",
      points: [
        "Your servers, your data",
        "MIT — commercial use OK",
        "Change anything",
        "No limits, ever",
      ],
      cta: "View on GitHub",
    },
    hosted: {
      name: "Hosted at tovayo.com",
      tag: "Free & unlimited",
      body: "Zero setup — we run it for you. Connect your bot and go. Your data, deletable anytime.",
      points: [
        "Zero setup",
        "We run & update it",
        "Free & unlimited",
        "Delete your data anytime",
      ],
      cta: "Start free",
    },
  },
  trust: {
    title: "Honest about your data",
    body: "Conversations are stored on our servers so the assistant has context. You can delete your account and all of your data at any time — instantly and irreversibly.",
    privacy: "Privacy Policy",
    terms: "Terms of Service",
  },
  faq: {
    title: "Questions, answered",
    items: [
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
        "Yes — Settings, Danger zone, Delete account permanently erases your business and all its data, with no undo.",
      ],
      ["Which channels are supported?", "Telegram today. WhatsApp is planned."],
      [
        "Do I need to know how to code?",
        "No, for the hosted service — you just connect a bot token. Self-hosting needs some technical setup.",
      ],
    ],
  },
  name: {
    eyebrow: "The name",
    title: 'Why "Tovayo"?',
    intro:
      "Say it slow — to·va·yo. In Spanish, va means “it's running.” The rest is pure motion.",
    words: [
      { word: "vaya", lang: "Spanish", meaning: "“go — there you go!”" },
      { word: "ayo", lang: "Indonesian", meaning: "“let's go!”" },
      { word: "yo", lang: "Spanish", meaning: "“I — I've got it”" },
    ],
    punchline:
      "An assistant that never stops moving: a customer writes and it's on it — vaya, ayo! — and it's the “yo”, the “I”, that answers for you. There, done — voilà.",
  },
  cta: {
    title: "Your front desk, handled.",
    sub: "Free, unlimited, and open source. Set it up in minutes.",
  },
  voice: {
    title: "Voice receptionist — premium",
    sub: "A real phone number that answers, talks naturally, and books — in English, Spanish, or Russian. Only on tovayo.com.",
    pricing: "$1 per call · pay-as-you-go",
    comingSoon: "Billing coming soon",
    signInCta: "Sign in with Google to try the live demo",
    signInNote: "We only use your email to follow up about early access.",
    callPrompt: "Call to try it — speak in the language you choose:",
    error: "Couldn't verify your sign-in. Please try again.",
  },
  footer: {
    brand: "Tovayo — open-source AI front desk.",
    github: "GitHub",
    terms: "Terms",
    privacy: "Privacy",
    start: "Start free",
  },
};

const es: Copy = {
  nav: {
    demo: "Demo",
    how: "Cómo funciona",
    features: "Funciones",
    faq: "Preguntas",
    github: "Ver en GitHub",
    start: "Empieza gratis",
  },
  hero: {
    badge: "Gratis y de código abierto · MIT",
    title1: "Una ",
    titleAccent: "recepción con IA",
    title2: " gratis para tu pequeño negocio",
    sub: "Responde a clientes, agenda citas y envía recordatorios — 24/7, en su idioma. Usa el código abierto, o déjanos alojarlo por ti. Ambas opciones gratis.",
    ctaPrimary: "Empieza gratis",
    ctaSecondary: "Ver en GitHub",
    trust: "Gratis e ilimitado · Código abierto · Sin tarjeta",
  },
  demo: {
    eyebrow: "Mira cómo funciona",
    title: "Habla con un asistente real",
    subA: "Esto es ",
    subB: " — un salón de demostración con horario en vivo. Pide una hora y reserva de verdad; verás cada paso que da el agente.",
    headerSub: "Corte · horario de demo · siempre reservable",
    online: "En línea",
    agentSteps: "Pasos del agente",
    cta: "Empieza gratis para probarlo",
    sample: [
      {
        who: "user",
        text: "¡Hola! ¿Puedo cortarme el pelo mañana por la tarde?",
      },
      {
        who: "bot",
        text: "¡Claro! Mañana por la tarde tengo libres 14:00, 14:30 y 15:15. ¿Cuál te viene bien?",
        trace: [
          { kind: "think", text: "El cliente quiere un corte mañana PM" },
          {
            kind: "tool",
            text: 'find_availability(service: "Haircut", around: "tomorrow 14:00")',
          },
          { kind: "result", text: "3 huecos libres -> 14:00, 14:30, 15:15" },
        ],
      },
      { who: "user", text: "14:30, por favor" },
      {
        who: "bot",
        text: "¡Reservado! Corte mañana a las 14:30 (60 min). Recibirás un recordatorio antes.",
        trace: [
          {
            kind: "tool",
            text: 'book(service: "Haircut", start: "tomorrow 14:30")',
          },
        ],
      },
    ],
  },
  how: {
    title: "Listo en tres pasos",
    steps: [
      {
        title: "Regístrate y describe tu negocio",
        body: "Añade tus servicios, horarios y preguntas frecuentes — o auto-aloja el código abierto si prefieres.",
      },
      {
        title: "Conecta tu bot de Telegram",
        body: "Pega un token de bot. Ese es todo el setup — sin servidores, sin código.",
      },
      {
        title: "Tus clientes escriben al bot",
        body: "Tovayo responde, reserva, reprograma y recuerda — en el idioma de tu cliente.",
      },
    ],
  },
  features: {
    title: "Todo lo que hace una recepción",
    sub: "Sin el CRM torpe, los mensajes perdidos ni la cuota mensual.",
    items: [
      {
        title: "Responde con tu info",
        body: "Responde con tus propios servicios, precios, horarios y FAQ — nunca se inventa nada.",
      },
      {
        title: "Reserva de verdad",
        body: "Reserva, reprograma y cancela citas reales, con protección contra dobles reservas.",
      },
      {
        title: "Recoge lo que necesitas",
        body: "Pide los datos que requieras antes de reservar — p. ej. una fecha de nacimiento para un astrólogo.",
      },
      {
        title: "Reduce las ausencias",
        body: "Envía recordatorios antes de cada cita para que los clientes acudan.",
      },
      {
        title: "Puedes tomar el control",
        body: "Entra en cualquier chat y responde tú mismo; la IA se aparta hasta que se lo devuelvas.",
      },
      {
        title: "Cuatro idiomas",
        body: "Inglés, español, ruso y chino — en el idioma del cliente, de serie.",
      },
    ],
  },
  run: {
    title: "Dos formas de usarlo. Ambas gratis.",
    sub: 'No es "gratis vs pago" — opciones equivalentes. Elige la que encaje.',
    selfHost: {
      name: "Auto-alojado",
      tag: "Gratis para siempre",
      body: "Toma el código, ejecútalo en tus servidores, cambia lo que quieras. Licencia MIT — uso comercial permitido.",
      points: [
        "Tus servidores, tus datos",
        "MIT — uso comercial OK",
        "Cambia lo que sea",
        "Sin límites, nunca",
      ],
      cta: "Ver en GitHub",
    },
    hosted: {
      name: "Alojado en tovayo.com",
      tag: "Gratis e ilimitado",
      body: "Cero configuración — lo ejecutamos por ti. Conecta tu bot y listo. Tus datos, borrables cuando quieras.",
      points: [
        "Cero configuración",
        "Lo ejecutamos y actualizamos",
        "Gratis e ilimitado",
        "Borra tus datos cuando quieras",
      ],
      cta: "Empieza gratis",
    },
  },
  trust: {
    title: "Honestos con tus datos",
    body: "Las conversaciones se guardan en nuestros servidores para que el asistente tenga contexto. Puedes borrar tu cuenta y todos tus datos en cualquier momento — al instante e irreversible.",
    privacy: "Política de privacidad",
    terms: "Términos del servicio",
  },
  faq: {
    title: "Preguntas, resueltas",
    items: [
      [
        "¿De verdad es gratis?",
        "Sí. El servicio alojado en tovayo.com es gratis e ilimitado, sin tarjeta. El código tiene licencia MIT, así que auto-alojarlo también es gratis.",
      ],
      [
        "¿Puedo usarlo comercialmente?",
        "Por supuesto. La licencia MIT te permite usar, modificar y ejecutar el código para cualquier fin, incluido el comercial.",
      ],
      [
        "¿Dónde están mis datos?",
        "En nuestros servidores (servicio alojado), o en los tuyos si auto-alojas. No los vendemos ni entrenamos modelos con tus conversaciones.",
      ],
      [
        "¿Puedo borrar todo?",
        "Sí — Ajustes, Zona peligrosa, Eliminar cuenta borra permanentemente tu negocio y todos sus datos, sin vuelta atrás.",
      ],
      ["¿Qué canales admite?", "Telegram hoy. WhatsApp está planeado."],
      [
        "¿Necesito saber programar?",
        "No, para el servicio alojado — solo conectas un token de bot. Auto-alojar requiere algo de setup técnico.",
      ],
    ],
  },
  name: {
    eyebrow: "El nombre",
    title: '¿Por qué "Tovayo"?',
    intro:
      "Dilo despacio — to·va·yo. En español, va es “está en marcha”. El resto es puro movimiento.",
    words: [
      { word: "vaya", lang: "Español", meaning: "«vaya — ¡ahí lo tienes!»" },
      { word: "ayo", lang: "Indonesio", meaning: "«¡vamos!»" },
      { word: "yo", lang: "Español", meaning: "«yo — yo me encargo»" },
    ],
    punchline:
      "Un asistente que no para: un cliente escribe y ya está en ello — ¡vaya, ayo! — y es el “yo” quien responde por ti. Listo — voilà.",
  },
  cta: {
    title: "Tu recepción, resuelta.",
    sub: "Gratis, ilimitado y de código abierto. Configúralo en minutos.",
  },
  voice: {
    title: "Recepcionista de voz — premium",
    sub: "Un número real que contesta, habla con naturalidad y agenda — en inglés, español o ruso. Solo en tovayo.com.",
    pricing: "$1 por llamada · pago por uso",
    comingSoon: "Cobro próximamente",
    signInCta: "Inicia sesión con Google para probar la demo",
    signInNote:
      "Solo usamos tu correo para contactarte sobre el acceso anticipado.",
    callPrompt: "Llama para probarlo — habla en el idioma que elijas:",
    error: "No pudimos verificar tu inicio de sesión. Inténtalo de nuevo.",
  },
  footer: {
    brand: "Tovayo — recepción con IA de código abierto.",
    github: "GitHub",
    terms: "Términos",
    privacy: "Privacidad",
    start: "Empieza gratis",
  },
};

const ru: Copy = {
  nav: {
    demo: "Демо",
    how: "Как это работает",
    features: "Возможности",
    faq: "Вопросы",
    github: "Открыть на GitHub",
    start: "Начать бесплатно",
  },
  hero: {
    badge: "Бесплатно и open source · MIT",
    title1: "Бесплатный ",
    titleAccent: "ИИ-ресепшн",
    title2: " для вашего малого бизнеса",
    sub: "Отвечает клиентам, записывает на приём и шлёт напоминания — 24/7, на их языке. Берите открытый код или дайте нам хостить за вас. И то, и другое — бесплатно.",
    ctaPrimary: "Начать бесплатно",
    ctaSecondary: "Открыть на GitHub",
    trust: "Бесплатно и без лимитов · Открытый код · Без карты",
  },
  demo: {
    eyebrow: "Посмотрите, как это работает",
    title: "Поговорите с настоящим ассистентом",
    subA: "Это ",
    subB: " — демо-салон с живым расписанием. Спросите про время и реально запишитесь; вы увидите каждый шаг агента.",
    headerSub: "Стрижка · демо-расписание · всегда доступно",
    online: "Онлайн",
    agentSteps: "Шаги агента",
    cta: "Начните бесплатно и попробуйте сами",
    sample: [
      {
        who: "user",
        text: "Привет! Можно подстричься завтра во второй половине дня?",
      },
      {
        who: "bot",
        text: "Конечно! Завтра днём свободно 14:00, 14:30 и 15:15. Какое время удобно?",
        trace: [
          {
            kind: "think",
            text: "Клиент хочет стрижку завтра во второй половине дня",
          },
          {
            kind: "tool",
            text: 'find_availability(service: "Haircut", around: "tomorrow 14:00")',
          },
          { kind: "result", text: "3 свободных слота -> 14:00, 14:30, 15:15" },
        ],
      },
      { who: "user", text: "14:30, пожалуйста" },
      {
        who: "bot",
        text: "Записал! Стрижка завтра в 14:30 (60 мин). Перед началом пришлю напоминание.",
        trace: [
          {
            kind: "tool",
            text: 'book(service: "Haircut", start: "tomorrow 14:30")',
          },
        ],
      },
    ],
  },
  how: {
    title: "Запуск за три шага",
    steps: [
      {
        title: "Зарегистрируйтесь и опишите бизнес",
        body: "Добавьте услуги, часы работы и FAQ — или разверните открытый код сами.",
      },
      {
        title: "Подключите Telegram-бота",
        body: "Вставьте один токен бота. Это вся настройка — без серверов и кода.",
      },
      {
        title: "Клиенты пишут вашему боту",
        body: "Tovayo отвечает, записывает, переносит и напоминает — на языке клиента.",
      },
    ],
  },
  features: {
    title: "Всё, что делает ресепшн",
    sub: "Без громоздкой CRM, потерянных сообщений и ежемесячного счёта.",
    items: [
      {
        title: "Отвечает по вашим данным",
        body: "Отвечает из ваших услуг, цен, часов и FAQ — ничего не выдумывает.",
      },
      {
        title: "Записывает по-настоящему",
        body: "Записывает, переносит и отменяет реальные записи, с защитой от двойного бронирования.",
      },
      {
        title: "Собирает что нужно",
        body: "Спрашивает нужные данные перед записью — например, дату рождения для астролога.",
      },
      {
        title: "Снижает неявки",
        body: "Шлёт напоминания перед каждой записью, чтобы клиенты приходили.",
      },
      {
        title: "Вы можете подключиться",
        body: "Зайдите в любой диалог и отвечайте сами; ИИ замолкает, пока вы не вернёте.",
      },
      {
        title: "Четыре языка",
        body: "Английский, испанский, русский и китайский — на языке клиента, из коробки.",
      },
    ],
  },
  run: {
    title: "Два способа запустить. Оба бесплатны.",
    sub: "Не «бесплатно против платно» — равноправные варианты. Выбирайте свой.",
    selfHost: {
      name: "Свой хостинг",
      tag: "Бесплатно навсегда",
      body: "Берите код, разворачивайте на своих серверах, меняйте что угодно. Лицензия MIT — коммерческое использование разрешено.",
      points: [
        "Ваши серверы, ваши данные",
        "MIT — коммерция разрешена",
        "Меняйте что угодно",
        "Никаких лимитов",
      ],
      cta: "Открыть на GitHub",
    },
    hosted: {
      name: "Хостинг на tovayo.com",
      tag: "Бесплатно и без лимитов",
      body: "Никакой настройки — мы хостим за вас. Подключите бота и работайте. Данные удаляются в любой момент.",
      points: [
        "Никакой настройки",
        "Мы хостим и обновляем",
        "Бесплатно и без лимитов",
        "Удалите данные в любой момент",
      ],
      cta: "Начать бесплатно",
    },
  },
  trust: {
    title: "Честно о ваших данных",
    body: "Диалоги хранятся на наших серверах, чтобы у ассистента был контекст. Вы можете удалить аккаунт и все свои данные в любой момент — мгновенно и безвозвратно.",
    privacy: "Политика конфиденциальности",
    terms: "Условия использования",
  },
  faq: {
    title: "Ответы на вопросы",
    items: [
      [
        "Это правда бесплатно?",
        "Да. Хостинг на tovayo.com — бесплатно и без лимитов, без карты. Код под лицензией MIT, так что свой хостинг тоже бесплатен.",
      ],
      [
        "Можно использовать в коммерции?",
        "Конечно. Лицензия MIT позволяет использовать, изменять и запускать код для любых целей, включая коммерческие.",
      ],
      [
        "Где мои данные?",
        "На наших серверах (для хостинга) или на ваших, если разворачиваете сами. Мы их не продаём и не обучаем модели на ваших диалогах.",
      ],
      [
        "Можно удалить всё?",
        "Да — Настройки, Опасная зона, Удалить аккаунт безвозвратно стирает бизнес и все его данные, без отмены.",
      ],
      ["Какие каналы поддерживаются?", "Telegram сейчас. WhatsApp — в планах."],
      [
        "Нужно ли уметь программировать?",
        "Нет, для хостинга — вы просто подключаете токен бота. Свой хостинг требует технической настройки.",
      ],
    ],
  },
  name: {
    eyebrow: "Имя",
    title: "Почему «Tovayo»?",
    intro:
      "Произнеси медленно — to·va·yo. По-испански va — «идёт, работает». А дальше — сплошное движение.",
    words: [
      { word: "vaya", lang: "испанский", meaning: "«давай — ну вот!»" },
      { word: "ayo", lang: "индонезийский", meaning: "«пошли! / го!»" },
      { word: "yo", lang: "испанский", meaning: "«я — я разберусь»" },
    ],
    punchline:
      "Ассистент, который не стоит на месте: клиент написал — и оно уже на этом — ¡vaya, ayo! — и это «yo», то самое «я», что отвечает за тебя. Готово — voilà.",
  },
  cta: {
    title: "Ваш ресепшн — под контролем.",
    sub: "Бесплатно, без лимитов и с открытым кодом. Настройка за минуты.",
  },
  voice: {
    title: "Голосовой ресепшн — премиум",
    sub: "Настоящий номер, который отвечает, говорит естественно и записывает — на английском, испанском или русском. Только на tovayo.com.",
    pricing: "$1 за звонок · оплата по факту",
    comingSoon: "Оплата скоро",
    signInCta: "Войдите через Google, чтобы попробовать демо",
    signInNote: "Используем ваш email только чтобы связаться о раннем доступе.",
    callPrompt: "Позвоните и попробуйте — говорите на выбранном языке:",
    error: "Не удалось подтвердить вход. Попробуйте ещё раз.",
  },
  footer: {
    brand: "Tovayo — открытый ИИ-ресепшн.",
    github: "GitHub",
    terms: "Условия",
    privacy: "Конфиденциальность",
    start: "Начать бесплатно",
  },
};

const zh: Copy = {
  nav: {
    demo: "演示",
    how: "工作原理",
    features: "功能",
    faq: "常见问题",
    github: "在 GitHub 查看",
    start: "免费开始",
  },
  hero: {
    badge: "免费开源 · MIT",
    title1: "为您的小型企业打造的免费 ",
    titleAccent: "AI 前台",
    title2: "",
    sub: "全天候用客户的语言回复、预约并发送提醒。可使用开源代码，或让我们为您托管。两者都免费。",
    ctaPrimary: "免费开始",
    ctaSecondary: "在 GitHub 查看",
    trust: "免费无限 · 开源 · 无需信用卡",
  },
  demo: {
    eyebrow: "看看它如何工作",
    title: "与真实的助手对话",
    subA: "这是 ",
    subB: "——一个带实时排期的演示沙龙。问个时间并真正预约，您会看到智能体的每一步。",
    headerSub: "理发 · 演示排期 · 始终可约",
    online: "在线",
    agentSteps: "智能体步骤",
    cta: "免费开始，亲自试试",
    sample: [
      { who: "user", text: "你好！明天下午能理发吗？" },
      {
        who: "bot",
        text: "当然！明天下午我有 14:00、14:30 和 15:15 空闲。您方便哪个时间？",
        trace: [
          { kind: "think", text: "客户想明天下午理发" },
          {
            kind: "tool",
            text: 'find_availability(service: "Haircut", around: "tomorrow 14:00")',
          },
          { kind: "result", text: "3 个空闲时段 -> 14:00, 14:30, 15:15" },
        ],
      },
      { who: "user", text: "请定 14:30" },
      {
        who: "bot",
        text: "已预约！明天 14:30 理发（60 分钟）。开始前会给您提醒。",
        trace: [
          {
            kind: "tool",
            text: 'book(service: "Haircut", start: "tomorrow 14:30")',
          },
        ],
      },
    ],
  },
  how: {
    title: "三步上线",
    steps: [
      {
        title: "注册并描述您的业务",
        body: "添加服务、营业时间和常见问题——或者自行部署开源代码。",
      },
      {
        title: "连接您的 Telegram 机器人",
        body: "粘贴一个机器人令牌。这就是全部设置——无服务器、无代码。",
      },
      {
        title: "客户给您的机器人发消息",
        body: "Tovayo 用客户的语言回复、预约、改期并提醒。",
      },
    ],
  },
  features: {
    title: "前台该做的，一样不少",
    sub: "没有笨重的 CRM、漏掉的消息或每月账单。",
    items: [
      {
        title: "依据您的信息回答",
        body: "基于您的服务、价格、时间和常见问题回复——绝不胡编。",
      },
      {
        title: "真正预约",
        body: "预约、改期和取消真实的约会，并防止重复预约。",
      },
      {
        title: "按需收集信息",
        body: "在预约前询问您需要的信息——例如占星师需要的出生日期。",
      },
      { title: "减少爽约", body: "在每次预约前发送提醒，让客户准时到场。" },
      {
        title: "您可以接手",
        body: "进入任意对话亲自回复；在您交还前，AI 会暂停。",
      },
      {
        title: "四种语言",
        body: "英语、西班牙语、俄语和中文——开箱即用，使用客户的语言。",
      },
    ],
  },
  run: {
    title: "两种运行方式，都免费。",
    sub: "不是“免费 vs 付费”——同等的一流选项。挑适合您的。",
    selfHost: {
      name: "自行部署",
      tag: "永久免费",
      body: "拿走代码，部署到您的服务器，随意修改。MIT 许可——允许商用。",
      points: ["您的服务器，您的数据", "MIT——可商用", "随意修改", "永无限制"],
      cta: "在 GitHub 查看",
    },
    hosted: {
      name: "托管在 tovayo.com",
      tag: "免费无限",
      body: "零设置——我们为您运行。连接机器人即可。数据随时可删除。",
      points: ["零设置", "我们运行并更新", "免费无限", "随时删除您的数据"],
      cta: "免费开始",
    },
  },
  trust: {
    title: "对您的数据坦诚相待",
    body: "对话存储在我们的服务器上，以便助手拥有上下文。您可以随时删除账户和所有数据——即时且不可恢复。",
    privacy: "隐私政策",
    terms: "服务条款",
  },
  faq: {
    title: "问题，已解答",
    items: [
      [
        "真的免费吗？",
        "是的。tovayo.com 的托管服务免费且无限制，无需信用卡。代码采用 MIT 许可，因此自行部署也免费。",
      ],
      [
        "可以用于商业用途吗？",
        "当然可以。MIT 许可允许您出于任何目的使用、修改和运行代码，包括商业用途。",
      ],
      [
        "我的数据在哪里？",
        "在我们的服务器上（托管服务），或您自己的服务器上（自行部署）。我们不出售数据，也不用您的对话训练模型。",
      ],
      [
        "可以删除全部吗？",
        "可以——设置、危险区域、删除账户会永久清除您的企业及其所有数据，无法撤销。",
      ],
      ["支持哪些渠道？", "目前是 Telegram。WhatsApp 在计划中。"],
      [
        "需要会编程吗？",
        "托管服务不需要——您只需连接一个机器人令牌。自行部署需要一些技术设置。",
      ],
    ],
  },
  name: {
    eyebrow: "名字的由来",
    title: '为什么叫 "Tovayo"？',
    intro: "慢慢念——to·va·yo。西班牙语 va 意为「运转中」——其余全是动感。",
    words: [
      { word: "vaya", lang: "西班牙语", meaning: "「走起——这就好了！」" },
      { word: "ayo", lang: "印尼语", meaning: "「走吧！」" },
      { word: "yo", lang: "西班牙语", meaning: "「我——交给我」" },
    ],
    punchline:
      "一个永不停歇的助手：客户一发来消息，它立刻行动——¡vaya, ayo!——而那个「yo」（「我」）替你回应。搞定——voilà。",
  },
  cta: { title: "前台，交给我们。", sub: "免费、无限、开源。几分钟即可设置。" },
  voice: {
    title: "语音接待员 — 高级功能",
    sub: "一个真实的电话号码，会接听、自然交谈并预约 — 支持英语、西班牙语或俄语。仅在 tovayo.com 提供。",
    pricing: "每通电话 $1 · 按量付费",
    comingSoon: "计费即将上线",
    signInCta: "使用 Google 登录以试用演示",
    signInNote: "我们仅使用您的邮箱就抢先体验与您联系。",
    callPrompt: "拨打试用 — 用您选择的语言交谈：",
    error: "无法验证您的登录，请重试。",
  },
  footer: {
    brand: "Tovayo——开源 AI 前台。",
    github: "GitHub",
    terms: "条款",
    privacy: "隐私",
    start: "免费开始",
  },
};

const COPY: Record<Locale, Copy> = { en, es, ru, zh };

const I18nContext = createContext<{
  locale: Locale;
  setLocale: (l: Locale) => void;
  c: Copy;
}>({
  locale: "en",
  setLocale: () => {},
  c: en,
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  useEffect(() => {
    const saved = readLocaleCookie();
    if (saved && (LOCALES as readonly string[]).includes(saved)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- restore the shared language on mount
      setLocaleState(saved as Locale);
    }
  }, []);
  const setLocale = (l: Locale) => {
    setLocaleState(l);
    writeLocaleCookie(l);
  };
  return (
    <I18nContext.Provider value={{ locale, setLocale, c: COPY[locale] }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
