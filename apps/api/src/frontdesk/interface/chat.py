"""A synchronous web-chat endpoint: talk to the assistant, get its reply back.

Same assistant, same tools, same typed core as the channels — only the transport
differs (one HTTP request/response instead of a webhook + outbound send). It also
collects the agent's reasoning and tool calls so the UI can show its work.
"""

import logging
import uuid
from dataclasses import replace

from fastapi import APIRouter
from pydantic import BaseModel

from frontdesk.application.assistant import Assistant, AssistantDeps
from frontdesk.application.ports import Clock, InboundMessage
from frontdesk.domain.enums import Channel
from frontdesk.infrastructure.channels.composite import CapturingMessaging

_logger = logging.getLogger("frontdesk.chat")


class TraceStep(BaseModel):
    kind: str  # "thought" | "tool"
    text: str | None = None
    tool: str | None = None
    args: dict[str, object] | None = None
    result: str | None = None


class ChatRequest(BaseModel):
    text: str
    session: str


class ChatReply(BaseModel):
    reply: str
    trace: list[TraceStep] = []


class _TraceCollector:
    """Implements AssistantObserver: records the agent's steps for the UI and the log."""

    def __init__(self) -> None:
        self.steps: list[TraceStep] = []

    async def on_thought(self, text: str) -> None:
        self.steps.append(TraceStep(kind="thought", text=text))
        _logger.debug("thought text=%r", text)

    async def on_tool(self, name: str, args: dict[str, object], result: str) -> None:
        self.steps.append(TraceStep(kind="tool", tool=name, args=args, result=result))
        _logger.debug("tool name=%s args=%s result=%r", name, args, result)


def build_chat_router(deps: AssistantDeps, to_address: str, clock: Clock) -> APIRouter:
    router = APIRouter()

    @router.post("/api/chat")
    async def chat(request: ChatRequest) -> ChatReply:
        # One customer per browser session, so the conversation history persists.
        capture = CapturingMessaging()
        collector = _TraceCollector()
        assistant = Assistant(replace(deps, messaging=capture), observer=collector)
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
        reply = capture.replies[-1] if capture.replies else "…"
        return ChatReply(reply=reply, trace=collector.steps)

    return router
