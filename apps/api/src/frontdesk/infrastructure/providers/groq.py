"""Groq-backed supervisor: labels what a draft reply claims, so the loop can verify each claim.

Groq exposes an OpenAI-compatible chat-completions endpoint, so the call shape mirrors the main
provider — but the job is different (one short classification, no tools), so it is its own
adapter. Best-effort: if Groq is unreachable it returns no claims (no guardrail) rather than
blocking the customer's reply.
"""

import logging

import httpx

from frontdesk.application.ports import ReplyClaim

_logger = logging.getLogger("frontdesk.supervisor")

# The classifier emits short tags; we map them back to claims. Keep it terse and deterministic.
_TAGS = {
    "TIMES": ReplyClaim.OFFERS_TIMES,
    "BOOKING": ReplyClaim.CONFIRMS_BOOKING,
    "LIST": ReplyClaim.LISTS_APPOINTMENTS,
}
_SYSTEM_PROMPT = (
    "You classify a draft message a booking assistant is about to send to a customer. Reply with "
    "the space-separated tags that apply, or NONE:\n"
    "TIMES — it offers, lists, or proposes specific available appointment times to choose from.\n"
    "BOOKING — it states that a booking, reschedule, or cancellation has just been done.\n"
    "LIST — it states, lists, or counts the customer's existing/upcoming appointments.\n"
    "Output only the tags (e.g. 'BOOKING LIST') or 'NONE'. No other words."
)
_MAX_TOKENS = 10  # a few short tags at most


class GroqReplyClaimClassifier:
    """Classifies, via Groq, which claims a draft reply makes about times/bookings/appointments."""

    def __init__(
        self, *, api_key: str, model: str, client: httpx.AsyncClient, base_url: str
    ) -> None:
        self._key = api_key
        self._model = model
        self._client = client
        self._base = base_url.rstrip("/")

    async def classify(self, message: str) -> frozenset[ReplyClaim]:
        if not message.strip():
            return frozenset()
        payload = {
            "model": self._model,
            "max_tokens": _MAX_TOKENS,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        }
        try:
            response = await self._client.post(
                f"{self._base}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self._key}"},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            # Best-effort guardrail: a supervisor outage must never block the customer's reply.
            _logger.warning("reply-claim supervisor unavailable: %s", error)
            return frozenset()
        content = response.json()["choices"][0]["message"].get("content") or ""
        return frozenset(_TAGS[tag] for tag in content.upper().split() if tag in _TAGS)


class NullReplyClaimClassifier:
    """Used when no supervisor is configured: the claim guardrail is a no-op."""

    async def classify(self, message: str) -> frozenset[ReplyClaim]:
        return frozenset()
