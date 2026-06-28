"""File + console logging for the real data flow.

One place configures the ``frontdesk`` logger tree so every adapter that already
logs (events, messaging, the assistant observer, the webhook) lands in a rotating
file you can grep to trace what really happened. See the /goal: "логгирование в
файлы (чтобы разбирать поток реальных данных)".
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str = "INFO", log_file: str = "") -> None:
    """Send the ``frontdesk.*`` logs to the console and, if set, a rotating file."""
    root = logging.getLogger("frontdesk")
    root.setLevel(level.upper())
    root.handlers.clear()
    root.propagate = False

    formatter = logging.Formatter(_FORMAT)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_file:
        directory = os.path.dirname(log_file)
        if directory:
            os.makedirs(directory, exist_ok=True)  # so a fresh container/volume just works
        file_handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
