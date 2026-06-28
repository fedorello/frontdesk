"""Groq-backed supervisor: a fast classifier that flags replies offering bookable times.

Groq exposes an OpenAI-compatible chat-completions endpoint, so the call shape mirrors the main
provider — but the job is different (one yes/no classification, no tools), so it is its own
adapter. The detector is best-effort: if Groq is unreachable it returns False (no guardrail)
rather than blocking the customer's reply.
"""

import logging

import httpx

_logger = logging.getLogger("frontdesk.supervisor")

# Keep the classifier terse and deterministic: one word out, no room to ramble.
_SYSTEM_PROMPT = (
    "You are a strict classifier for a booking assistant. You receive a draft message the "
    "assistant is about to send to a customer. Answer YES if the message offers, lists, or "
    "proposes specific available appointment times for the customer to choose from. Answer NO "
    "for anything else: greetings, prices, questions, or confirming an already-made booking. "
    "Reply with exactly one word: YES or NO."
)
_MAX_TOKENS = 2  # one word ("YES"/"NO") is a single token; 2 leaves a safe margin


class GroqAvailabilityDetector:
    """Classifies, via Groq, whether a draft reply offers the customer bookable times."""

    def __init__(
        self, *, api_key: str, model: str, client: httpx.AsyncClient, base_url: str
    ) -> None:
        self._key = api_key
        self._model = model
        self._client = client
        self._base = base_url.rstrip("/")

    async def mentions_available_slots(self, message: str) -> bool:
        if not message.strip():
            return False
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
            _logger.warning("availability supervisor unavailable: %s", error)
            return False
        content = response.json()["choices"][0]["message"].get("content") or ""
        return content.strip().upper().startswith("YES")


class NullAvailabilityClaimDetector:
    """Used when no supervisor is configured: the availability guardrail is a no-op."""

    async def mentions_available_slots(self, message: str) -> bool:
        return False
