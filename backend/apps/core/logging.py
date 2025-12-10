"""Custom logging formatters for Loki integration."""

import json
import logging
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Compatible with Loki and other log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_record["extra"] = record.extra

        # Add task info for Celery
        if hasattr(record, "task_id"):
            log_record["task_id"] = record.task_id
        if hasattr(record, "task_name"):
            log_record["task_name"] = record.task_name

        return json.dumps(log_record)

