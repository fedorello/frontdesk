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
}
_SYSTEM_PROMPT = (
    "You classify a draft message a booking assistant is about to send to a customer. The message "
    "may be in ANY language. Check EACH tag independently — both can apply. Output the "
    "space-separated tags that apply, or NONE:\n"
    "TIMES — it offers, lists, or proposes specific available appointment times to choose from.\n"
    "BOOKING — it states that a booking, reschedule, or cancellation has just been done.\n"
    "Output only the tags (e.g. 'TIMES BOOKING') or 'NONE'. No other words."
)
_MAX_TOKENS = 10  # a few short tags at most (e.g. 'TIMES BOOKING')


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


_NORMALIZE_PROMPT = (
    "You clean ONE value a customer gave for a form field, in ANY language. Return the essential "
    "value in its natural base form. Rules: (1) drop leading prepositions and filler in ANY "
    "language (like 'in', 'at', 'the city of'); (2) for a place, give just the place name in its "
    "dictionary/nominative form; (3) for a time, keep the WHOLE remaining phrase, including the "
    "part of day (morning/afternoon/evening); (4) KEEP spelled-out numbers, times and dates as "
    "WORDS — never turn them into digits; (5) keep the customer's language — do NOT translate. "
    "Reply with ONLY the cleaned value, nothing else. Examples: field 'Birth place' value 'in the "
    "city of London' -> London; field 'Birth time' value 'at half past two in the afternoon' -> "
    "half past two in the afternoon."
)
# gpt-oss is a reasoning model: its thinking consumes the completion budget, so leave ample room
# (a tiny cap starves the actual answer and the value comes back unchanged), and keep reasoning
# shallow — a form-field cleanup needs no deep chain of thought. The cap is a ceiling, not a cost:
# temperature-0 output stops as soon as the value is emitted, so headroom is free.
_NORMALIZE_MAX_TOKENS = 5000
_NORMALIZE_REASONING_EFFORT = "low"


class GroqFactNormalizer:
    """Cleans a captured fact value via a cheap Groq model. Best-effort: keeps the raw value if
    Groq is unreachable, so remembering a fact never fails on a normalization hiccup."""

    def __init__(
        self, *, api_key: str, model: str, client: httpx.AsyncClient, base_url: str
    ) -> None:
        self._key = api_key
        self._model = model
        self._client = client
        self._base = base_url.rstrip("/")

    async def normalize(self, field: str, value: str) -> str:
        clean = value.strip()
        if not clean:
            return clean
        payload = {
            "model": self._model,
            "max_tokens": _NORMALIZE_MAX_TOKENS,
            "temperature": 0,
            "reasoning_effort": _NORMALIZE_REASONING_EFFORT,
            "messages": [
                {"role": "system", "content": _NORMALIZE_PROMPT},
                {"role": "user", "content": f"field '{field}' value '{clean}'"},
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
            _logger.warning("fact normalizer unavailable: %s", error)
            return clean
        content = response.json()["choices"][0]["message"].get("content") or ""
        return content.strip() or clean


class NullFactNormalizer:
    """Used when no Groq key is configured: keep the raw value (only trimmed)."""

    async def normalize(self, field: str, value: str) -> str:
        return value.strip()
