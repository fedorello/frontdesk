"""Start linking an owner's Telegram chat: issue a one-time code and send the dashboard link.

The owner opens the link while signed in as the owner; the confirm endpoint then binds the chat.
See docs/OWNER_TELEGRAM_NOTIFICATIONS.md.
"""

import logging
from datetime import timedelta

from frontdesk.application.ports import (
    BusinessRepository,
    Clock,
    IdGenerator,
    OwnerNotificationSender,
    OwnerTelegramLinkRepository,
    TelegramLinkCodeStore,
)
from frontdesk.domain.errors import LinkCodeError
from frontdesk.domain.ids import BusinessId, LinkCode
from frontdesk.domain.notifications import (
    LinkCodeProblem,
    OwnerTelegramLink,
    TelegramLinkCode,
    redeem_problem,
)

_logger = logging.getLogger("frontdesk.owner_linking")

# Long enough to switch apps and sign in, short enough to limit exposure of a leaked link.
LINK_CODE_TTL = timedelta(minutes=15)
_DEFAULT_LOCALE = "en"
_LINK_MESSAGE = {
    "en": "To get booking notifications in this chat, open this link while signed in as the "
    "business owner (it expires in {minutes} minutes):\n{link}",
    "es": "Para recibir avisos de reservas en este chat, abre este enlace habiendo iniciado "
    "sesión como propietario (caduca en {minutes} minutos):\n{link}",
    "ru": "Чтобы получать уведомления о записях в этот чат, откройте ссылку, войдя как "
    "владелец бизнеса (действует {minutes} минут):\n{link}",
    "zh": "若要在此聊天接收预约通知，请在以企业所有者身份登录后打开此链接"
    "（{minutes} 分钟内有效）：\n{link}",
}


class OwnerLinking:
    """Issues a one-time link code for a Telegram chat and sends the owner the dashboard link."""

    def __init__(
        self,
        codes: TelegramLinkCodeStore,
        links: OwnerTelegramLinkRepository,
        businesses: BusinessRepository,
        sender: OwnerNotificationSender,
        ids: IdGenerator,
        clock: Clock,
        dashboard_url: str,
    ) -> None:
        self._codes = codes
        self._links = links
        self._businesses = businesses
        self._sender = sender
        self._ids = ids
        self._clock = clock
        self._dashboard_url = dashboard_url.rstrip("/")

    async def start(self, business_id: BusinessId, chat_id: str, telegram_name: str) -> None:
        code = LinkCode(self._ids.new())
        expires_at = self._clock.now() + LINK_CODE_TTL
        await self._codes.issue(
            TelegramLinkCode(code, business_id, chat_id, telegram_name, expires_at)
        )
        business = await self._businesses.find(business_id)
        locale = business.locale if business is not None else _DEFAULT_LOCALE
        template = _LINK_MESSAGE.get(locale) or _LINK_MESSAGE[_DEFAULT_LOCALE]
        message = template.format(
            link=f"{self._dashboard_url}/connect-telegram?code={code}",
            minutes=int(LINK_CODE_TTL.total_seconds() // 60),
        )
        await self._sender.send(business_id, chat_id, message)
        _logger.info("owner link code issued business=%s", business_id)

    async def confirm(self, business_id: BusinessId, code: LinkCode) -> OwnerTelegramLink:
        """Redeem a code (once, unexpired, own business) and bind the owner's chat.

        Raises LinkCodeError(problem) when the code is missing, used, expired, or another tenant's.
        """
        record = await self._codes.get(code)
        problem = redeem_problem(record, business_id, self._clock.now())
        if problem is not None:
            _logger.warning(
                "owner link confirm rejected business=%s problem=%s", business_id, problem
            )
            raise LinkCodeError(problem)
        assert record is not None  # redeem_problem returns NOT_FOUND when record is None
        # Claim the code atomically BEFORE binding, so two concurrent confirms can't both succeed.
        if not await self._codes.mark_used(code):
            _logger.warning("owner link confirm lost the redeem race business=%s", business_id)
            raise LinkCodeError(LinkCodeProblem.USED)
        link = OwnerTelegramLink(business_id, record.chat_id, record.telegram_name)
        await self._links.upsert(link)
        _logger.info("owner telegram linked business=%s", business_id)
        return link
