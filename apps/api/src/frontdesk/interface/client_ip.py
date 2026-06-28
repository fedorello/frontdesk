"""Best-effort client IP for rate-limit keys.

Behind Railway's (or any) reverse proxy the socket peer is the proxy, so prefer the first
hop in ``X-Forwarded-For`` when present.
"""

from fastapi import Request


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
