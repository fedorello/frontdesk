"""Money validation."""

import pytest

from frontdesk.domain.money import Money


def test_valid_money() -> None:
    money = Money(4999, "USD")

    assert money.amount_cents == 4999
    assert money.currency == "USD"


@pytest.mark.parametrize(
    ("amount_cents", "currency"),
    [(-1, "USD"), (100, "US"), (100, "USDD"), (100, "12A")],
)
def test_invalid_money(amount_cents: int, currency: str) -> None:
    with pytest.raises(ValueError, match=r"negative|currency"):
        Money(amount_cents, currency)
