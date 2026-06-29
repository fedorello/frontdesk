"""The pure redeem rule for one-time Telegram link codes."""

from datetime import UTC, datetime, timedelta

from frontdesk.domain.ids import BusinessId, LinkCode
from frontdesk.domain.notifications import (
    LinkCodeProblem,
    TelegramLinkCode,
    redeem_problem,
)

NOW = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)


def _code(*, business: str = "biz", used: bool = False, expires_in: int = 10) -> TelegramLinkCode:
    return TelegramLinkCode(
        LinkCode("c1"),
        BusinessId(business),
        "chat-1",
        "Owner",
        NOW + timedelta(minutes=expires_in),
        used=used,
    )


def test_redeem_problem_is_none_for_a_fresh_code_of_the_right_business() -> None:
    assert redeem_problem(_code(), BusinessId("biz"), NOW) is None


def test_redeem_problem_flags_a_missing_code() -> None:
    assert redeem_problem(None, BusinessId("biz"), NOW) is LinkCodeProblem.NOT_FOUND


def test_redeem_problem_flags_a_used_code() -> None:
    assert redeem_problem(_code(used=True), BusinessId("biz"), NOW) is LinkCodeProblem.USED


def test_redeem_problem_flags_an_expired_code() -> None:
    assert redeem_problem(_code(expires_in=-1), BusinessId("biz"), NOW) is LinkCodeProblem.EXPIRED


def test_redeem_problem_flags_another_businesss_code() -> None:
    problem = redeem_problem(_code(business="other"), BusinessId("biz"), NOW)
    assert problem is LinkCodeProblem.WRONG_BUSINESS
