"""The web-chat endpoint runs the real assistant and returns its reply."""

import httpx
from fastapi import FastAPI

from frontdesk.application.ports import Completion, ToolCall
from frontdesk.domain.models import MAX_MESSAGE_LENGTH
from frontdesk.interface.chat import build_chat_router
from tests.application.world import BIZ_ADDR, World, build_world


def _tool(call_id: str, name: str, args: dict[str, object]) -> Completion:
    return Completion(None, (ToolCall(call_id, name, args),))


def _client(world: World) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(build_chat_router(world.deps, BIZ_ADDR, world.clock))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_chat_books_and_returns_the_reply() -> None:
    world = build_world(
        [
            _tool("1", "find_availability", {"service": "Haircut"}),
            _tool("2", "book", {"service": "Haircut", "start": "2026-06-26T15:00:00+00:00"}),
            Completion("You're booked for 3pm! ✅"),
        ]
    )

    async with _client(world) as client:
        response = await client.post("/api/chat", json={"text": "haircut at 3pm", "session": "s1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"].endswith("You're booked for 3pm! ✅")
    assert len(world.appointments.appointments) == 1
    tools = [step["tool"] for step in payload["trace"] if step["kind"] == "tool"]
    assert tools == ["find_availability", "book"]


async def test_chat_answers_without_booking() -> None:
    world = build_world(
        [
            _tool("1", "answer_question", {"topic": "hours"}),
            Completion("We're open 9 to 17, Monday to Friday."),
        ]
    )

    async with _client(world) as client:
        response = await client.post("/api/chat", json={"text": "your hours?", "session": "s2"})

    assert response.json()["reply"].endswith("We're open 9 to 17, Monday to Friday.")
    assert world.appointments.appointments == {}


async def test_chat_rejects_an_oversized_message() -> None:
    world = build_world([Completion("hi")])

    async with _client(world) as client:
        response = await client.post(
            "/api/chat", json={"text": "x" * (MAX_MESSAGE_LENGTH + 1), "session": "s"}
        )

    assert response.status_code == 422  # rejected by max_length before the assistant runs
