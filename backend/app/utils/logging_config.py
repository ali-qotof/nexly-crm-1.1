"""Structured JSON logging (القاعدة 60): request id, endpoint, status, latency, error category.
لا يُسجَّل أي password/token/secret/DATABASE_URL — لا يوجد مكان في هذا الملف يقرأ body أو headers."""
import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        for key in ("request_id", "method", "path", "status", "latency_ms", "error_category"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("nexly")
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    root.propagate = False
