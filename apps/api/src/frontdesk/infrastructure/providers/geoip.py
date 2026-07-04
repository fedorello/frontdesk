"""Best-effort IP → country lookup, used to enrich the operator's admin view.

Resolves the country name from a public IP via ipapi.co (no key, free tier). Best-effort by design:
any failure, timeout, or private/loopback IP yields "" — a sign-up must never fail or stall because
a geo lookup did. See ports.GeoIpResolver.
"""

import ipaddress
import logging

import httpx

_logger = logging.getLogger("frontdesk.geoip")

_TIMEOUT = 2.5  # a sign-up waits at most this long on the lookup
_MAX_COUNTRY_LEN = 60  # a real country name is short; longer means we got an error blob


def _is_public(ip: str) -> bool:
    """True only for a globally routable IP — skip loopback/private/link-local (and junk)."""
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


class HttpGeoIpResolver:
    """Looks up the country name for a public IP via ipapi.co (best-effort)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def country(self, ip: str) -> str:
        if not _is_public(ip):
            return ""
        try:
            response = await self._client.get(
                f"https://ipapi.co/{ip}/country_name/", timeout=_TIMEOUT
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            _logger.warning("geoip lookup failed: %s", error)
            return ""
        name = response.text.strip()
        # ipapi.co returns a plain country name on success, or an error blob otherwise.
        if not name or len(name) > _MAX_COUNTRY_LEN or "error" in name.lower() or "{" in name:
            return ""
        return name


class NullGeoIpResolver:
    """Used when geo lookups are disabled (or in tests): always unknown."""

    async def country(self, ip: str) -> str:
        return ""
