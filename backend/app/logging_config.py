"""Structured JSON logging to stdout, so Loki/Promtail can parse every field."""
import json
import logging
import sys
import time
from datetime import datetime, timezone

from flask import g, request

_RESERVED = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        entry.update({k: v for k, v in vars(record).items() if k not in _RESERVED})
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def init_logging(app):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(app.config["LOG_LEVEL"])

    access = logging.getLogger("travel.access")

    @app.before_request
    def _start_timer():
        g.request_start = time.perf_counter()

    @app.after_request
    def _log_request(response):
        if request.path in ("/healthz", "/readyz", "/metrics"):
            return response
        duration = time.perf_counter() - g.get("request_start", time.perf_counter())
        access.info(
            "request",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
            },
        )
        return response
