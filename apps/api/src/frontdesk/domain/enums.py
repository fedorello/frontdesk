"""Closed sets of domain values."""

from enum import StrEnum


class Channel(StrEnum):
    """How we reach a customer."""

    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class AppointmentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"


class RiskTier(StrEnum):
    """Drives the approval gate: safe runs automatically, sensitive pauses."""

    SAFE = "safe"
    SENSITIVE = "sensitive"


class MessageRole(StrEnum):
    CUSTOMER = "customer"
    ASSISTANT = "assistant"
    OWNER = "owner"  # the business owner, replying by hand through the bot
    SYSTEM = "system"
    TOOL = "tool"


class NotificationEvent(StrEnum):
    """A schedule change the business owner is notified about."""

    BOOKED = "booked"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
