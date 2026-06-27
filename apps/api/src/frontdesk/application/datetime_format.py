"""Localized date/time for the deterministic messages a customer receives.

strftime's %a/%b are English-only, so booking receipts and cancel/reschedule notices
came out as "Tue 30 Jun" even on a Russian bot. These tables render the weekday and month
in the business's own language without pulling in a heavy i18n dependency.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from frontdesk.domain.models import Business

# Indexed by Python's weekday(): Monday = 0 … Sunday = 6.
_WEEKDAYS = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "es": ("lun", "mar", "mié", "jue", "vie", "sáb", "dom"),
    "ru": ("пн", "вт", "ср", "чт", "пт", "сб", "вс"),
    "zh": ("周一", "周二", "周三", "周四", "周五", "周六", "周日"),
}

# Indexed by month - 1.
_MONTHS = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"),
    "ru": ("янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"),
    "zh": ("1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"),
}

_TEMPLATE = {
    "en": "{wd} {day} {mon} {hh}:{mm}",
    "es": "{wd} {day} {mon} {hh}:{mm}",
    "ru": "{wd} {day} {mon} {hh}:{mm}",
    "zh": "{wd} {mon}{day}日 {hh}:{mm}",
}


def format_when(moment: datetime, business: Business) -> str:
    """A friendly local datetime in the business's time zone and language."""
    local = moment.astimezone(ZoneInfo(business.timezone))
    locale = business.locale if business.locale in _WEEKDAYS else "en"
    return _TEMPLATE[locale].format(
        wd=_WEEKDAYS[locale][local.weekday()],
        day=local.day,
        mon=_MONTHS[locale][local.month - 1],
        hh=f"{local.hour:02d}",
        mm=f"{local.minute:02d}",
    )
