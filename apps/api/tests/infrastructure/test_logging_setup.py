"""File logging captures the real data flow; the observer logs thoughts and tools."""

import logging
from pathlib import Path

from frontdesk.infrastructure.logging_setup import configure_logging
from frontdesk.infrastructure.observers import LoggingObserver


def test_configure_logging_writes_to_file(tmp_path: Path) -> None:
    log_file = tmp_path / "data-flow.log"
    configure_logging("INFO", str(log_file))
    try:
        logging.getLogger("frontdesk.webhook").info("inbound business=biz1 text=%r", "hi there")
        for handler in logging.getLogger("frontdesk").handlers:
            handler.flush()

        contents = log_file.read_text()
        assert "inbound business=biz1" in contents
        assert "hi there" in contents
    finally:
        configure_logging("INFO", "")  # reset so the file handler releases tmp_path


def test_configure_logging_creates_a_missing_directory(tmp_path: Path) -> None:
    log_file = tmp_path / "nested" / "logs" / "app.log"  # parent dirs don't exist yet
    configure_logging("INFO", str(log_file))
    try:
        logging.getLogger("frontdesk.auth").info("login ok account=acc-1")
        for handler in logging.getLogger("frontdesk").handlers:
            handler.flush()
        assert log_file.exists()
        assert "login ok account=acc-1" in log_file.read_text()
    finally:
        configure_logging("INFO", "")


async def test_logging_observer_records_thoughts_and_tools(tmp_path: Path) -> None:
    log_file = tmp_path / "agent.log"
    configure_logging("DEBUG", str(log_file))  # thoughts/tools are DEBUG (they carry PII)
    try:
        observer = LoggingObserver("biz1")
        await observer.on_thought("Let me check availability")
        await observer.on_tool("book", {"slot": "09:00"}, "booked")
        for handler in logging.getLogger("frontdesk").handlers:
            handler.flush()

        contents = log_file.read_text()
        assert "thought business=biz1" in contents
        assert "tool business=biz1 name=book" in contents
        assert "booked" in contents
    finally:
        configure_logging("INFO", "")
