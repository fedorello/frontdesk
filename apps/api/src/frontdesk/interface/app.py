"""The production composition root: build the real product from Settings.

`uvicorn frontdesk.interface.app:create_production_app --factory` serves the
webhook API wired to Postgres, a real LLM provider, and the live channels.
"""

from datetime import datetime

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import (
    ApprovalGate,
    Clock,
    IdGenerator,
    LlmProvider,
    MessagingPort,
    SecretCipher,
)
from frontdesk.core.settings import Settings
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate, PendingApprovals
from frontdesk.infrastructure.channels.composite import LoggingMessaging, RoutingMessaging
from frontdesk.infrastructure.channels.telegram import TelegramMessaging
from frontdesk.infrastructure.channels.whatsapp import WhatsAppMessaging
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.events import LoggingEventPublisher
from frontdesk.infrastructure.logging_setup import configure_logging
from frontdesk.infrastructure.memory import InMemoryIdempotency
from frontdesk.infrastructure.postgres.adapters import (
    SqlAccountRepository,
    SqlAppointmentRepository,
    SqlBusinessRepository,
    SqlCalendar,
    SqlChannelBindingRepository,
    SqlConversationRepository,
    SqlCustomerRepository,
    SqlLlmConfigRepository,
    SqlReminderStore,
    SqlResourceRepository,
    SqlServiceRepository,
    SqlTelegramBotRepository,
    SqlUsageStore,
)
from frontdesk.infrastructure.providers.anthropic import AnthropicProvider
from frontdesk.infrastructure.providers.openai import OpenAiProvider
from frontdesk.infrastructure.secrets import FernetCipher
from frontdesk.infrastructure.system import FixedClock, SystemClock, UuidIdGenerator
from frontdesk.interface.approvals import build_approvals_router
from frontdesk.interface.auth import build_auth_router, make_owner_guard
from frontdesk.interface.business_config import build_llm_config_router
from frontdesk.interface.chat import build_chat_router
from frontdesk.interface.config_api import build_config_router
from frontdesk.interface.metrics_api import build_metrics_router
from frontdesk.interface.read_api import build_read_router
from frontdesk.interface.telegram_connect import build_telegram_connect_router
from frontdesk.interface.telegram_inbound import TelegramInbound
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


def build_assistant_deps(
    settings: Settings,
    sessions: async_sessionmaker[AsyncSession],
    ids: IdGenerator,
    clock: Clock,
    client: httpx.AsyncClient,
    gate: ApprovalGate,
) -> AssistantDeps:
    """Assemble the assistant's dependency graph — shared by the API and the poller.

    `messaging` and `llm` are the global defaults; tenant transports replace them
    per business at dispatch time.
    """
    reminders = SqlReminderStore(sessions)
    calendar = SqlCalendar(sessions, ids, clock)
    events = LoggingEventPublisher()
    scheduler = ReminderScheduler(reminders, ids, clock)
    return AssistantDeps(
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
        gate,
        clock,
    )


def create_production_app() -> FastAPI:
    settings = Settings()
    configure_logging(settings.log_level, settings.log_file)
    engine = create_engine(settings.database_url)
    sessions = make_session_factory(engine)
    clock = build_clock(settings)
    ids = UuidIdGenerator()
    client = httpx.AsyncClient(timeout=30)

    pending_approvals = PendingApprovals()
    cipher = build_cipher(settings)
    telegram_bots = SqlTelegramBotRepository(sessions, cipher)
    llm_configs = SqlLlmConfigRepository(sessions, cipher)
    accounts = SqlAccountRepository(sessions)
    usage = SqlUsageStore(sessions)
    guard = make_owner_guard(accounts, settings.secret_key, settings.token_max_age_seconds)

    # Dogfoods airlock-hitl (ADR-0005): sensitive actions gated for human approval.
    deps = build_assistant_deps(
        settings, sessions, ids, clock, client, AirlockApprovalGate(pending_approvals)
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
    telegram_inbound = TelegramInbound(deps, llm_configs, usage, settings, client)
    app.include_router(build_chat_router(deps, settings.demo_to_address, clock))
    app.include_router(build_approvals_router(pending_approvals))
    app.include_router(build_telegram_router(telegram_inbound, telegram_bots))
    app.include_router(build_auth_router(accounts, SqlBusinessRepository(sessions), ids, settings))
    app.include_router(build_llm_config_router(llm_configs, guard))
    app.include_router(
        build_config_router(
            SqlBusinessRepository(sessions),
            SqlServiceRepository(sessions),
            SqlResourceRepository(sessions),
            guard,
        )
    )
    app.include_router(
        build_telegram_connect_router(
            telegram_bots, SqlChannelBindingRepository(sessions), settings, client, guard
        )
    )
    app.include_router(
        build_read_router(
            SqlAppointmentRepository(sessions),
            SqlServiceRepository(sessions),
            SqlConversationRepository(sessions),
            guard,
        )
    )
    app.include_router(build_metrics_router(usage, settings, clock, guard))
    return app
