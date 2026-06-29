"""The platform-analytics use case: assemble the operator overview from the read ports.

Pure orchestration over the analytics Protocols (ADR-0012). The derived rates
(no-show, cancellation, funnel conversion) are computed here — business logic, not SQL or
UI — each guarded against a zero denominator.
"""

from frontdesk.application.analytics_models import (
    ActivationFunnel,
    BusinessSummary,
    DailyCount,
    DateWindow,
    DirectoryQuery,
    FunnelConversion,
    Overview,
    TimeseriesMetric,
)
from frontdesk.application.ports import (
    BusinessDirectoryRepository,
    Clock,
    PlatformSummaryRepository,
    PlatformTimeseriesRepository,
)


def _ratio(numerator: int, denominator: int) -> float:
    """A fraction in [0.0, 1.0]; an empty denominator yields 0.0 rather than dividing by zero."""
    return numerator / denominator if denominator else 0.0


def _funnel_conversion(funnel: ActivationFunnel) -> FunnelConversion:
    """Each later funnel stage as a fraction of the businesses that signed up."""
    signed_up = funnel.signed_up
    return FunnelConversion(
        connected_pct=_ratio(funnel.connected_channel, signed_up),
        received_message_pct=_ratio(funnel.received_message, signed_up),
        booked_pct=_ratio(funnel.booked_appointment, signed_up),
    )


class PlatformAnalytics:
    """Read-only, cross-tenant operator analytics (ADR-0012)."""

    def __init__(
        self,
        summary: PlatformSummaryRepository,
        timeseries: PlatformTimeseriesRepository,
        directory: BusinessDirectoryRepository,
        clock: Clock,
    ) -> None:
        self._summary = summary
        self._timeseries = timeseries
        self._directory = directory
        self._clock = clock

    async def overview(self) -> Overview:
        """Headline totals + funnel + derived rates, as of now."""
        totals = await self._summary.totals(self._clock.now())
        funnel = await self._summary.activation_funnel()
        appointments = totals.appointments
        return Overview(
            totals=totals,
            funnel=funnel,
            funnel_conversion=_funnel_conversion(funnel),
            no_show_rate=_ratio(appointments.no_show, appointments.total),
            cancellation_rate=_ratio(appointments.cancelled, appointments.total),
        )

    async def timeseries(self, metric: TimeseriesMetric, window: DateWindow) -> list[DailyCount]:
        """One daily-bucketed metric over the window."""
        return await self._timeseries.daily(metric, window)

    async def businesses(self, query: DirectoryQuery) -> tuple[list[BusinessSummary], int]:
        """A page of the business directory: the rows plus the total matching count."""
        return await self._directory.page(query)
