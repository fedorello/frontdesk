"""Notify the business owner, through their bot, on every customer-driven schedule change.

An EventListener: it reacts to AppointmentBooked / Rescheduled / Cancelled and messages the
owner's linked Telegram chat (if enabled). AppointmentConfirmed is intentionally not handled —
that is the owner's own action. See docs/OWNER_TELEGRAM_NOTIFICATIONS.md.
"""

import logging

from frontdesk.application.datetime_format import format_when
from frontdesk.application.ports import (
    AppointmentBooked,
    AppointmentCancelled,
    AppointmentEvent,
    AppointmentRepository,
    AppointmentRescheduled,
    BusinessRepository,
    CustomerRepository,
    DomainEvent,
    OwnerNotificationSender,
    OwnerTelegramLinkRepository,
    ServiceRepository,
)
from frontdesk.domain.enums import AppointmentStatus, NotificationEvent

_logger = logging.getLogger("frontdesk.owner_notifier")

# Which schedule change each event represents. A registry, not an if/elif switch (OCP).
_KIND_BY_EVENT: dict[type[DomainEvent], NotificationEvent] = {
    AppointmentBooked: NotificationEvent.BOOKED,
    AppointmentRescheduled: NotificationEvent.RESCHEDULED,
    AppointmentCancelled: NotificationEvent.CANCELLED,
}

# Localized owner messages. Falls back to "en". {confirm} is only filled for a pending booking;
# str.format ignores it for the templates that omit it.
_TEMPLATES: dict[tuple[str, NotificationEvent], str] = {
    (
        "en",
        NotificationEvent.BOOKED,
    ): "🆕 New booking: **{service}** — {when}\nCustomer: {customer}{confirm}",
    (
        "en",
        NotificationEvent.RESCHEDULED,
    ): "🔁 Rescheduled: **{service}** — now {when}\nCustomer: {customer}",
    (
        "en",
        NotificationEvent.CANCELLED,
    ): "❌ Cancelled: **{service}** — {when}\nCustomer: {customer}",
    (
        "es",
        NotificationEvent.BOOKED,
    ): "🆕 Nueva reserva: **{service}** — {when}\nCliente: {customer}{confirm}",
    (
        "es",
        NotificationEvent.RESCHEDULED,
    ): "🔁 Reprogramada: **{service}** — ahora {when}\nCliente: {customer}",
    (
        "es",
        NotificationEvent.CANCELLED,
    ): "❌ Cancelada: **{service}** — {when}\nCliente: {customer}",
    (
        "ru",
        NotificationEvent.BOOKED,
    ): "🆕 Новая запись: **{service}** — {when}\nКлиент: {customer}{confirm}",
    (
        "ru",
        NotificationEvent.RESCHEDULED,
    ): "🔁 Перенос: **{service}** — теперь {when}\nКлиент: {customer}",
    ("ru", NotificationEvent.CANCELLED): "❌ Отмена: **{service}** — {when}\nКлиент: {customer}",
    (
        "zh",
        NotificationEvent.BOOKED,
    ): "🆕 新预约：**{service}** — {when}\n客户：{customer}{confirm}",
    (
        "zh",
        NotificationEvent.RESCHEDULED,
    ): "🔁 已改期：**{service}** — 现在 {when}\n客户：{customer}",
    ("zh", NotificationEvent.CANCELLED): "❌ 已取消：**{service}** — {when}\n客户：{customer}",
}
_CONFIRM_SUFFIX = {
    "en": "\n⚠️ Needs your confirmation — open the dashboard.",
    "es": "\n⚠️ Necesita tu confirmación — abre el panel.",
    "ru": "\n⚠️ Нужно ваше подтверждение — откройте панель.",
    "zh": "\n⚠️ 需要您确认 — 请打开后台。",
}
_CUSTOMER_FALLBACK = {"en": "a customer", "es": "un cliente", "ru": "клиент", "zh": "客户"}
_DEFAULT_LOCALE = "en"


class OwnerNotifier:
    """Sends the owner a Telegram message when an appointment is booked, moved, or cancelled."""

    def __init__(
        self,
        links: OwnerTelegramLinkRepository,
        appointments: AppointmentRepository,
        services: ServiceRepository,
        customers: CustomerRepository,
        businesses: BusinessRepository,
        sender: OwnerNotificationSender,
    ) -> None:
        self._links = links
        self._appointments = appointments
        self._services = services
        self._customers = customers
        self._businesses = businesses
        self._sender = sender

    async def on_event(self, event: DomainEvent) -> None:
        kind = _KIND_BY_EVENT.get(type(event))
        if kind is None or not isinstance(event, AppointmentEvent):
            return  # not a change the owner is notified about
        link = await self._links.get(event.business_id)
        if link is None or not link.notifications_enabled:
            _logger.info(
                "owner notify skipped business=%s kind=%s (no link/off)", event.business_id, kind
            )
            return
        message = await self._compose(kind, event)
        await self._sender.send(event.business_id, link.chat_id, message)
        _logger.info("owner notified business=%s kind=%s", event.business_id, kind)

    async def _compose(self, kind: NotificationEvent, event: AppointmentEvent) -> str:
        appointment = await self._appointments.get(event.appointment_id)
        service = await self._services.get(appointment.service_id)
        customer = await self._customers.get(appointment.customer_id)
        business = await self._businesses.get(event.business_id)
        locale = business.locale
        template = _TEMPLATES.get((locale, kind)) or _TEMPLATES[(_DEFAULT_LOCALE, kind)]
        needs_confirmation = (
            kind is NotificationEvent.BOOKED and appointment.status is AppointmentStatus.PENDING
        )
        return template.format(
            service=service.name,
            when=format_when(appointment.slot.starts_at, business),
            customer=customer.name
            or _CUSTOMER_FALLBACK.get(locale, _CUSTOMER_FALLBACK[_DEFAULT_LOCALE]),
            confirm=_CONFIRM_SUFFIX.get(locale, _CONFIRM_SUFFIX[_DEFAULT_LOCALE])
            if needs_confirmation
            else "",
        )
