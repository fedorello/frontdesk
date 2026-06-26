"""The production composition root: build the real product from Settings.

`uvicorn frontdesk.interface.app:create_production_app --factory` serves the
webhook API wired to Postgres, a real LLM provider, and the live channels.
"""

from datetime import datetime

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import Clock, LlmProvider, MessagingPort, SecretCipher
from frontdesk.core.settings import Settings
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate, PendingApprovals
from frontdesk.infrastructure.channels.composite import LoggingMessaging, RoutingMessaging
from frontdesk.infrastructure.channels.telegram import TelegramMessaging
from frontdesk.infrastructure.channels.whatsapp import WhatsAppMessaging
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.events import LoggingEventPublisher
from frontdesk.infrastructure.memory import InMemoryIdempotency
from frontdesk.infrastructure.postgres.adapters import (
    SqlAppointmentRepository,
    SqlBusinessRepository,
    SqlCalendar,
    SqlConversationRepository,
    SqlCustomerRepository,
    SqlLlmConfigRepository,
    SqlReminderStore,
    SqlServiceRepository,
    SqlTelegramBotRepository,
)
from frontdesk.infrastructure.providers.anthropic import AnthropicProvider
from frontdesk.infrastructure.providers.openai import OpenAiProvider
from frontdesk.infrastructure.secrets import FernetCipher
from frontdesk.infrastructure.system import FixedClock, SystemClock, UuidIdGenerator
from frontdesk.interface.approvals import build_approvals_router
from frontdesk.interface.chat import build_chat_router
from frontdesk.interface.telegram_webhook import build_telegram_router
from frontdesk.interface.webhooks import WebhookConfig, create_app


def build_clock(settings: Settings) -> Clock:
    if settings.fixed_now:
        return FixedClock(datetime.fromisoformat(settings.fixed_now))
    return SystemClock()


def build_cipher(settings: Settings) -> SecretCipher:
    return FernetCipher(settings.secret_key)


def build_provider(settings: Settings, client: httpx.AsyncClient) -> LlmProvider:
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            client=client,
            max_tokens=settings.llm_max_tokens,
        )
    return OpenAiProvider(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        client=client,
        base_url=settings.llm_base_url,
        max_tokens=settings.llm_max_tokens,
    )


def build_messaging(settings: Settings, client: httpx.AsyncClient) -> MessagingPort:
    whatsapp = (
        WhatsAppMessaging(
            token=settings.whatsapp_token,
            phone_number_id=settings.whatsapp_phone_number_id,
            client=client,
        )
        if settings.whatsapp_token
        else None
    )
    telegram = (
        TelegramMessaging(
            token=settings.telegram_token,
            bot_address=settings.telegram_bot_address,
            client=client,
        )
        if settings.telegram_token
        else None
    )
    return RoutingMessaging(whatsapp=whatsapp, telegram=telegram, fallback=LoggingMessaging())


def create_production_app() -> FastAPI:
    settings = Settings()
    engine = create_engine(settings.database_url)
    sessions = make_session_factory(engine)
    clock = build_clock(settings)
    ids = UuidIdGenerator()
    client = httpx.AsyncClient(timeout=30)

    reminders = SqlReminderStore(sessions)
    calendar = SqlCalendar(sessions, ids, clock)
    events = LoggingEventPublisher()
    scheduler = ReminderScheduler(reminders, ids, clock)
    pending_approvals = PendingApprovals()
    cipher = build_cipher(settings)
    telegram_bots = SqlTelegramBotRepository(sessions, cipher)
    llm_configs = SqlLlmConfigRepository(sessions, cipher)

    deps = AssistantDeps(
        build_provider(settings, client),
        SqlBusinessRepository(sessions),
        SqlCustomerRepository(sessions, ids),
        SqlConversationRepository(sessions),
        SqlServiceRepository(sessions),
        SqlAppointmentRepository(sessions),
        calendar,
        BookAppointment(calendar, scheduler, events),
        RescheduleAppointment(calendar, scheduler),
        CancelAppointment(calendar, reminders, events),
        build_messaging(settings, client),
        events,
        AirlockApprovalGate(pending_approvals),  # dogfoods airlock-hitl (ADR-0005)
        clock,
    )
    config = WebhookConfig(
        whatsapp_app_secret=settings.whatsapp_app_secret,
        whatsapp_verify_token=settings.whatsapp_verify_token,
        telegram_secret=settings.telegram_secret,
        telegram_bot_address=settings.telegram_bot_address,
    )
    app = create_app(assistant=Assistant(deps), idempotency=InMemoryIdempotency(), config=config)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_chat_router(deps, settings.demo_to_address, clock))
    app.include_router(build_approvals_router(pending_approvals))
    app.include_router(build_telegram_router(deps, telegram_bots, llm_configs, settings, client))
    return app
