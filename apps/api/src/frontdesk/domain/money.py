"""Money — integer minor units, never a float."""

from dataclasses import dataclass

_ISO_CURRENCY_LENGTH = 3


@dataclass(frozen=True, slots=True)
class Money:
    """An amount in minor units (cents) plus an ISO-4217 currency code."""

    amount_cents: int
    currency: str

    def __post_init__(self) -> None:
        if self.amount_cents < 0:
            raise ValueError("amount_cents must not be negative")
        if len(self.currency) != _ISO_CURRENCY_LENGTH or not self.currency.isalpha():
            raise ValueError("currency must be a 3-letter ISO-4217 code")
