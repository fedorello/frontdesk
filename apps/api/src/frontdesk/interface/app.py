"""The production composition root: build the real product from Settings.

`uvicorn frontdesk.interface.app:create_production_app --factory` serves the
webhook API wired to Postgres, a real LLM provider, and the live channels.
"""

import httpx
from fastapi import FastAPI

from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import LlmProvider, MessagingPort
from frontdesk.core.settings import Settings
from frontdesk.infrastructure.channels.composite import LoggingMessaging, RoutingMessaging
from frontdesk.infrastructure.channels.telegram import TelegramMessaging
from frontdesk.infrastructure.channels.whatsapp import WhatsAppMessaging
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.events import LoggingEventPublisher
from frontdesk.infrastructure.memory import AutoDecisionGate, InMemoryIdempotency
from frontdesk.infrastructure.postgres.adapters import (
    SqlAppointmentRepository,
    SqlBusinessRepository,
    SqlCalendar,
    SqlConversationRepository,
    SqlCustomerRepository,
    SqlReminderStore,
    SqlServiceRepository,
)
from frontdesk.infrastructure.providers.anthropic import AnthropicProvider
from frontdesk.infrastructure.providers.openai import OpenAiProvider
from frontdesk.infrastructure.system import SystemClock, UuidIdGenerator
from frontdesk.interface.webhooks import WebhookConfig, create_app


def build_provider(settings: Settings, client: httpx.AsyncClient) -> LlmProvider:
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(
            api_key=settings.llm_api_key, model=settings.llm_model, client=client
        )
    return OpenAiProvider(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        client=client,
        base_url=settings.llm_base_url,
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
    clock = SystemClock()
    ids = UuidIdGenerator()
    client = httpx.AsyncClient(timeout=30)

    reminders = SqlReminderStore(sessions)
    calendar = SqlCalendar(sessions, ids, clock)
    events = LoggingEventPublisher()
    scheduler = ReminderScheduler(reminders, ids, clock)

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
        AutoDecisionGate(approved=False),  # production-safe: every sensitive action is held
        clock,
    )
    config = WebhookConfig(
        whatsapp_app_secret=settings.whatsapp_app_secret,
        whatsapp_verify_token=settings.whatsapp_verify_token,
        telegram_secret=settings.telegram_secret,
        telegram_bot_address=settings.telegram_bot_address,
    )
    return create_app(assistant=Assistant(deps), idempotency=InMemoryIdempotency(), config=config)
