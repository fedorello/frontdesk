"""An AssistantObserver that logs the agent's reasoning and tool calls to the data-flow log."""

import logging

_logger = logging.getLogger("frontdesk.assistant")


class LoggingObserver:
    """Logs each thought and tool call so the real agent flow is traceable in the file log."""

    def __init__(self, business_id: str = "") -> None:
        self._business_id = business_id

    async def on_thought(self, text: str) -> None:
        _logger.debug("thought business=%s text=%r", self._business_id, text)

    async def on_tool(self, name: str, args: dict[str, object], result: str) -> None:
        _logger.debug(
            "tool business=%s name=%s args=%s result=%r", self._business_id, name, args, result
        )
