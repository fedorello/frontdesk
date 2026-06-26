"""A tiny stand-in for the Telegram Bot API.

Lets the full connect -> webhook -> book -> reply loop run live through the real
stack without a BotFather token: point ``FRONTDESK_TELEGRAM_API_BASE`` at this server
and it answers getMe/setWebhook/sendMessage/deleteWebhook, logging every call so you
can see the outbound reply that was delivered. See docs/reports/m3-report.md.

    python scripts/mock_telegram.py 8081 /tmp/mock-telegram.log
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
LOG = sys.argv[2] if len(sys.argv) > 2 else "/tmp/mock-telegram.log"


def log(line: str) -> None:
    with open(LOG, "a") as handle:
        handle.write(line + "\n")


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if "/getMe" in self.path:
            log("getMe")
            self._send(
                {"ok": True, "result": {"id": 42, "is_bot": True, "username": "tovayo_test_bot"}}
            )
        else:
            self._send({"ok": False})

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", 0))
        data = json.loads(self.rfile.read(length).decode()) if length else {}
        if "/setWebhook" in self.path:
            log(f"setWebhook url={data.get('url')} secret={data.get('secret_token')}")
            self._send({"ok": True})
        elif "/sendMessage" in self.path:
            log(f"sendMessage chat={data.get('chat_id')} text={data.get('text')!r}")
            self._send({"ok": True, "result": {"message_id": 1}})
        elif "/deleteWebhook" in self.path:
            log("deleteWebhook")
            self._send({"ok": True})
        else:
            self._send({"ok": True})

    def log_message(self, *args: object) -> None:  # silence default stderr logging
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
