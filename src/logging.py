import json
import logging
import sys
from datetime import datetime, timezone


def setup_logging(level: str = "INFO") -> None:
    logger = logging.getLogger("nearme")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if record.name != "root":
            entry["logger"] = record.name
        if record.funcName:
            entry["func"] = record.funcName
        if record.exc_info and record.exc_info[1]:
            entry["error"] = str(record.exc_info[1])
        return json.dumps(entry, ensure_ascii=False)


def get_logger(name: str = "nearme") -> logging.Logger:
    return logging.getLogger(name)