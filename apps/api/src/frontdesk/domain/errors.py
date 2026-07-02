"""Domain errors — raised by pure rules, mapped to replies/HTTP at the edge."""

from frontdesk.domain.notifications import LinkCodeProblem


class DomainError(Exception):
    """Base class for every error the domain raises."""


class SlotUnavailable(DomainError):
    """The requested slot is taken or falls outside working hours."""


class DoubleBooking(DomainError):
    """A resource would be booked twice for overlapping times (a race)."""


class LeadTimeViolation(DomainError):
    """The requested slot is too close to now (inside the lead time)."""


class InvalidTransition(DomainError):
    """A state-machine transition that is not allowed."""


class AppointmentNotFound(DomainError):
    """No appointment with the given id."""


class ServiceNotFound(DomainError):
    """No service with the given id."""


class TenantMismatch(DomainError):
    """A cross-business access — always a bug, must never happen."""


class UnknownFeature(DomainError):
    """A feature key that is not in the premium-feature registry (a config/routing bug)."""

    def __init__(self, key: str) -> None:
        super().__init__(f"unknown premium feature: {key}")
        self.key = key


class LinkCodeError(DomainError):
    """A Telegram link code could not be redeemed; ``problem`` says why (machine-readable)."""

    def __init__(self, problem: LinkCodeProblem) -> None:
        super().__init__(problem.value)
        self.problem = problem
