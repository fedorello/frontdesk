"""A synchronous web-chat endpoint: talk to the assistant, get its reply back.

Same assistant, same tools, same typed core as the channels — only the transport
differs (one HTTP request/response instead of a webhook + outbound send).
"""

import uuid
from dataclasses import replace

from fastapi import APIRouter
from pydantic import BaseModel

from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import Clock, InboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.infrastructure.channels.composite import CapturingMessaging


class ChatRequest(BaseModel):
    text: str
    session: str


class ChatReply(BaseModel):
    reply: str


def build_chat_router(deps: AssistantDeps, to_address: str, clock: Clock) -> APIRouter:
    router = APIRouter()

    @router.post("/api/chat")
    async def chat(request: ChatRequest) -> ChatReply:
        # One customer per browser session, so the conversation history persists.
        capture = CapturingMessaging()
        assistant = Assistant(replace(deps, messaging=capture))
        await assistant.handle(
            InboundMessage(
                channel=Channel.WHATSAPP,
                from_address=f"web:{request.session}",
                to_address=to_address,
                text=request.text,
                received_at=clock.now(),
                provider_message_id=f"web:{uuid.uuid4().hex}",
            )
        )
        return ChatReply(reply=capture.replies[-1] if capture.replies else "…")

    return router
