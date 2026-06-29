"""Best-effort client IP for rate-limit keys.

Behind a reverse proxy the socket peer is the proxy, so the real client IP comes from
``X-Forwarded-For``. A client can PREPEND arbitrary entries to that header, but each trusted
proxy APPENDS the address it actually saw — so the trustworthy value is ``trusted_proxy_hops``
positions from the RIGHT, not the left. Reading the left-most entry (the old behaviour) let a
client rotate a spoofed IP to dodge per-IP rate limits.
"""

from fastapi import Request


def client_ip(request: Request, trusted_proxy_hops: int = 1) -> str:
    """The client IP as recorded by the closest trusted proxy, resistant to header spoofing.

    Falls back to the socket peer when the forwarded chain is shorter than the trusted-hop count
    (e.g. a direct connection that bypassed the proxy) or when no peer is available.
    """
    parts = [
        hop.strip() for hop in request.headers.get("x-forwarded-for", "").split(",") if hop.strip()
    ]
    if trusted_proxy_hops >= 1 and len(parts) >= trusted_proxy_hops:
        return parts[-trusted_proxy_hops]
    return request.client.host if request.client else "unknown"
