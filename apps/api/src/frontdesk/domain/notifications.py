"""Owner Telegram notifications: the link, the one-time code, and the redeem rule.

Pure domain types and business rules — no infrastructure. See
docs/OWNER_TELEGRAM_NOTIFICATIONS.md.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from frontdesk.domain.ids import BusinessId, LinkCode


@dataclass(frozen=True, slots=True)
class OwnerTelegramLink:
    """The owner's linked Telegram chat for a business, and whether alerts are on."""

    business_id: BusinessId
    chat_id: str  # Telegram chat id, stored as text (matches customer.address)
    telegram_name: str  # display name / @username, shown back for verification
    notifications_enabled: bool = True


@dataclass(frozen=True, slots=True)
class TelegramLinkCode:
    """A one-time code proving a Telegram chat asked to be linked; short-lived."""

    code: LinkCode
    business_id: BusinessId
    chat_id: str
    telegram_name: str
    expires_at: datetime  # timezone-aware UTC
    used: bool = False


class LinkCodeProblem(StrEnum):
    """Why a link code cannot be redeemed (machine-readable; the edge maps it to HTTP)."""

    NOT_FOUND = "not_found"
    USED = "used"
    EXPIRED = "expired"
    WRONG_BUSINESS = "wrong_business"


def redeem_problem(
    code: TelegramLinkCode | None, business_id: BusinessId, now: datetime
) -> LinkCodeProblem | None:
    """The reason a code can't be redeemed, or None when it can (once, unexpired, own business)."""
    if code is None:
        return LinkCodeProblem.NOT_FOUND
    if code.used:
        return LinkCodeProblem.USED
    if code.expires_at <= now:
        return LinkCodeProblem.EXPIRED
    if code.business_id != business_id:
        return LinkCodeProblem.WRONG_BUSINESS
    return None
