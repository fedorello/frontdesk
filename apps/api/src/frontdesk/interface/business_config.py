"""Business configuration write-API (M2): the per-business LLM provider.

The API key is **write-only** — accepted on input, stored encrypted, and never
returned (only a 4-char hint). See ADR-0009.
"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from frontdesk.application.ports import LlmConfig, LlmConfigRepository
from frontdesk.domain.ids import BusinessId

_PROVIDERS = {"openai", "anthropic", "openrouter"}
Guard = Callable[..., Awaitable[None]] | None


class LlmConfigView(BaseModel):
    mode: str
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key_hint: str | None = None  # never the full key


class LlmConfigInput(BaseModel):
    mode: str  # "default" | "own"
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


def _view(config: LlmConfig) -> LlmConfigView:
    return LlmConfigView(
        mode=config.mode,
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        api_key_hint=config.api_key_hint,
    )


def build_llm_config_router(llm_configs: LlmConfigRepository, guard: Guard = None) -> APIRouter:
    router = APIRouter(dependencies=[Depends(guard)] if guard is not None else [])

    @router.get("/api/businesses/{business_id}/llm")
    async def get_llm(business_id: str) -> LlmConfigView:
        config = await llm_configs.get(BusinessId(business_id))
        return _view(config) if config is not None else LlmConfigView(mode="default")

    @router.put("/api/businesses/{business_id}/llm")
    async def put_llm(business_id: str, body: LlmConfigInput) -> LlmConfigView:
        if body.mode not in {"default", "own"}:
            raise HTTPException(422, "mode must be 'default' or 'own'")
        if body.mode == "own":
            if body.provider not in _PROVIDERS:
                raise HTTPException(422, f"provider must be one of {sorted(_PROVIDERS)}")
            if not body.model or not body.api_key:
                raise HTTPException(422, "own mode needs a model and an api_key")

        config = LlmConfig(
            BusinessId(business_id),
            body.mode,
            body.provider,
            body.model,
            body.base_url,
            body.api_key,
            body.api_key[-4:] if body.api_key else None,
        )
        await llm_configs.upsert(config)
        return _view(config)  # no api_key in the response

    return router
