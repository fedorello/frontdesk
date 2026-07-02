"""The production composition root: build the real product from Settings.

`uvicorn frontdesk.interface.app:create_production_app --factory` serves the
webhook API wired to Postgres, a real LLM provider, and the live channels.
"""

from collections.abc import Sequence
from datetime import datetime

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from frontdesk.application.analytics import PlatformAnalytics
from frontdesk.application.appointments import (
    BookAppointment,
    CancelAppointment,
    ConfirmAppointment,
    ReminderScheduler,
    RescheduleAppointment,
)
from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.entitlements import (
    FeatureCatalog,
    RequestFeature,
    ReviewFeatureRequest,
)
from frontdesk.application.owner_actions import (
    OwnerCancelAppointment,
    OwnerRescheduleAppointment,
    OwnerSendMessage,
    SetConversationHandoff,
)
from frontdesk.application.owner_linking import OwnerLinking
from frontdesk.application.owner_notifier import OwnerNotifier
from frontdesk.application.ports import (
    ApprovalGate,
    Clock,
    IdGenerator,
    LlmProvider,
    MessagingPort,
    ReplyClaimClassifier,
    SecretCipher,
)
from frontdesk.core.settings import PremiumFeatureConfig, Settings
from frontdesk.domain.entitlements import FeatureRegistry, PremiumFeature
from frontdesk.domain.ids import FeatureKey
from frontdesk.infrastructure.airlock_gate import AirlockApprovalGate
from frontdesk.infrastructure.channels.composite import LoggingMessaging, RoutingMessaging
from frontdesk.infrastructure.channels.telegram import (
    TelegramCustomerNotifier,
    TelegramMessaging,
    TelegramOwnerNotificationSender,
)
from frontdesk.infrastructure.channels.whatsapp import WhatsAppMessaging
from frontdesk.infrastructure.db import create_engine, make_session_factory
from frontdesk.infrastructure.events import DispatchingEventPublisher, LoggingEventListener
from frontdesk.infrastructure.google_oauth import HttpGoogleOAuthClient
from frontdesk.infrastructure.keys import session_signing_key
from frontdesk.infrastructure.logging_setup import configure_logging
from frontdesk.infrastructure.memory import InMemoryIdempotency
from frontdesk.infrastructure.postgres.adapters import (
    SqlAccountRepository,
    SqlAppointmentRepository,
    SqlApprovalStore,
    SqlBusinessEraser,
    SqlBusinessRepository,
    SqlCalendar,
    SqlChannelBindingRepository,
    SqlConversationRepository,
    SqlCustomerRepository,
    SqlLlmConfigRepository,
    SqlOwnerTelegramLinkRepository,
    SqlReminderStore,
    SqlResourceRepository,
    SqlServiceRepository,
    SqlTelegramBotRepository,
    SqlTelegramLinkCodeStore,
    SqlUsageStore,
)
from frontdesk.infrastructure.postgres.analytics import (
    SqlBusinessDirectoryRepository,
    SqlPlatformSummaryRepository,
    SqlPlatformTimeseriesRepository,
)
from frontdesk.infrastructure.postgres.entitlements import SqlEntitlementRepository
from frontdesk.infrastructure.providers.anthropic import AnthropicProvider
from frontdesk.infrastructure.providers.groq import (
    GroqReplyClaimClassifier,
    NullReplyClaimClassifier,
)
from frontdesk.infrastructure.providers.openai import OpenAiProvider
from frontdesk.infrastructure.rate_limit import InMemoryRateLimiter
from frontdesk.infrastructure.secrets import FernetCipher
from frontdesk.infrastructure.system import (
    FixedClock,
    SystemClock,
    SystemRandom,
    UuidIdGenerator,
)
from frontdesk.interface.account_api import build_account_router
from frontdesk.interface.admin_api import build_admin_router
from frontdesk.interface.admin_entitlements_api import build_admin_entitlements_router
from frontdesk.interface.appointments_api import build_appointments_router
from frontdesk.interface.approvals import build_approvals_router
from frontdesk.interface.auth import (
    build_auth_router,
    build_me_router,
    make_admin_guard,
    make_owner_guard,
)
from frontdesk.interface.business_config import build_llm_config_router
from frontdesk.interface.chat import build_chat_router
from frontdesk.interface.config_api import build_config_router
from frontdesk.interface.conversations_api import build_conversations_router
from frontdesk.interface.features_api import build_features_router
from frontdesk.interface.google_auth import build_google_auth_router
from frontdesk.interface.metrics_api import build_metrics_router
from frontdesk.interface.owner_telegram import build_owner_telegram_router
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


def feature_registry_from(features: Sequence[PremiumFeatureConfig]) -> FeatureRegistry:
    """Map the configured premium-feature catalog into the domain registry (config, not code)."""
    return FeatureRegistry(
        [PremiumFeature(FeatureKey(f.key), f.name, f.description, f.pricing) for f in features]
    )


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


def build_reply_classifier(settings: Settings, client: httpx.AsyncClient) -> ReplyClaimClassifier:
    """The Groq supervisor when configured; otherwise a no-op (the guardrail is off)."""
    if not settings.groq_api_key:
        return NullReplyClaimClassifier()
    return GroqReplyClaimClassifier(
        api_key=settings.groq_api_key,
        model=settings.supervisor_model,
        client=client,
        base_url=settings.groq_base_url,
    )


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
    scheduler = ReminderScheduler(reminders, ids, clock)
    businesses = SqlBusinessRepository(sessions)
    customers = SqlCustomerRepository(sessions, ids)
    services = SqlServiceRepository(sessions)
    appointments = SqlAppointmentRepository(sessions)
    # Owner notifications react to schedule-change events through the business's own bot.
    sender = TelegramOwnerNotificationSender(
        SqlTelegramBotRepository(sessions, build_cipher(settings)), client
    )
    owner_notifier = OwnerNotifier(
        SqlOwnerTelegramLinkRepository(sessions),
        appointments,
        services,
        customers,
        businesses,
        sender,
    )
    events = DispatchingEventPublisher([LoggingEventListener(), owner_notifier])
    return AssistantDeps(
        build_provider(settings, client),
        businesses,
        customers,
        SqlConversationRepository(sessions),
        services,
        appointments,
        calendar,
        BookAppointment(calendar, scheduler, events),
        RescheduleAppointment(calendar, scheduler, events),
        CancelAppointment(calendar, reminders, events),
        build_messaging(settings, client),
        events,
        gate,
        clock,
        build_reply_classifier(settings, client),
    )


def build_owner_linking(
    settings: Settings,
    sessions: async_sessionmaker[AsyncSession],
    ids: IdGenerator,
    clock: Clock,
    client: httpx.AsyncClient,
) -> OwnerLinking:
    """Owner-chat linking: issue codes and confirm them — shared by the API and the poller."""
    sender = TelegramOwnerNotificationSender(
        SqlTelegramBotRepository(sessions, build_cipher(settings)), client
    )
    return OwnerLinking(
        SqlTelegramLinkCodeStore(sessions),
        SqlOwnerTelegramLinkRepository(sessions),
        SqlBusinessRepository(sessions),
        sender,
        ids,
        clock,
        settings.dashboard_url,
    )


def create_production_app() -> FastAPI:
    settings = Settings()
    configure_logging(settings.log_level, settings.log_file)
    engine = create_engine(settings.database_url)
    sessions = make_session_factory(engine)
    clock = build_clock(settings)
    ids = UuidIdGenerator()
    client = httpx.AsyncClient(timeout=30)

    approval_store = SqlApprovalStore(sessions)
    cipher = build_cipher(settings)
    telegram_bots = SqlTelegramBotRepository(sessions, cipher)
    llm_configs = SqlLlmConfigRepository(sessions, cipher)
    accounts = SqlAccountRepository(sessions)
    usage = SqlUsageStore(sessions)
    guard = make_owner_guard(
        accounts, session_signing_key(settings.secret_key), settings.token_max_age_seconds
    )
    rate_limiter = InMemoryRateLimiter()

    # Dogfoods airlock-hitl (ADR-0005): sensitive actions gated for human approval.
    deps = build_assistant_deps(
        settings, sessions, ids, clock, client, AirlockApprovalGate(approval_store)
    )
    config = WebhookConfig(
        whatsapp_app_secret=settings.whatsapp_app_secret,
        whatsapp_verify_token=settings.whatsapp_verify_token,
        telegram_secret=settings.telegram_secret,
        telegram_bot_address=settings.telegram_bot_address,
    )
    app = create_app(assistant=Assistant(deps), idempotency=InMemoryIdempotency(), config=config)
    # Credentialed CORS for the cookie session: the origin must be explicit (never "*"),
    # so fall back to the dashboard origin when none is configured.
    cors_origins = [
        o.strip() for o in settings.cors_allow_origins.split(",") if o.strip() and o.strip() != "*"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or [settings.dashboard_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    owner_linking = build_owner_linking(settings, sessions, ids, clock, client)
    telegram_inbound = TelegramInbound(
        deps, llm_configs, usage, settings, client, SystemRandom(), owner_linking
    )
    app.include_router(build_chat_router(deps, settings.demo_to_address, clock))
    app.include_router(build_approvals_router(approval_store, guard))
    app.include_router(build_telegram_router(telegram_inbound, telegram_bots))
    app.include_router(
        build_owner_telegram_router(SqlOwnerTelegramLinkRepository(sessions), owner_linking, guard)
    )
    app.include_router(
        build_auth_router(
            accounts,
            SqlBusinessRepository(sessions),
            SqlResourceRepository(sessions),
            ids,
            settings,
            rate_limiter,
        )
    )
    app.include_router(
        build_google_auth_router(
            HttpGoogleOAuthClient(
                settings.google_client_id,
                settings.google_client_secret,
                settings.google_redirect_uri,
                client,
            ),
            accounts,
            SqlBusinessRepository(sessions),
            SqlResourceRepository(sessions),
            ids,
            settings,
            rate_limiter,
        )
    )
    app.include_router(build_llm_config_router(llm_configs, settings.allow_own_llm, guard))
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
    notifier = TelegramCustomerNotifier(telegram_bots, client, settings.telegram_api_base)
    app.include_router(
        build_appointments_router(
            ConfirmAppointment(deps.appointments, deps.calendar, deps.events),
            OwnerCancelAppointment(
                deps.appointments,
                deps.services,
                deps.businesses,
                deps.customers,
                deps.cancel,
                notifier,
            ),
            OwnerRescheduleAppointment(
                deps.appointments,
                deps.services,
                deps.businesses,
                deps.customers,
                deps.reschedule,
                notifier,
            ),
            guard,
        )
    )
    app.include_router(
        build_conversations_router(
            OwnerSendMessage(deps.customers, deps.businesses, deps.conversations, notifier, clock),
            SetConversationHandoff(deps.customers),
            guard,
        )
    )
    app.include_router(build_account_router(SqlBusinessEraser(sessions), guard))
    app.include_router(build_metrics_router(usage, settings, clock, guard))
    # Premium features & entitlements (docs/plans/premium-features-plan.md): the owner catalog +
    # self-serve request, behind the owner guard.
    feature_registry = feature_registry_from(settings.premium_features)
    entitlements = SqlEntitlementRepository(sessions)
    app.include_router(
        build_features_router(
            FeatureCatalog(feature_registry, entitlements),
            RequestFeature(feature_registry, entitlements, clock),
            guard,
        )
    )
    # Cross-tenant admin analytics (ADR-0012), behind the admin guard; /api/me for the client role.
    analytics = PlatformAnalytics(
        SqlPlatformSummaryRepository(sessions),
        SqlPlatformTimeseriesRepository(sessions),
        SqlBusinessDirectoryRepository(sessions),
        clock,
    )
    admin_guard = make_admin_guard(
        accounts, session_signing_key(settings.secret_key), settings.token_max_age_seconds
    )
    app.include_router(build_admin_router(analytics, admin_guard))
    # Operator management of premium-feature entitlements (Phase 3, ADR-0013): approve/suspend.
    app.include_router(
        build_admin_entitlements_router(
            entitlements,
            ReviewFeatureRequest(feature_registry, entitlements, clock),
            admin_guard,
        )
    )
    app.include_router(build_me_router(accounts, settings))
    return app
