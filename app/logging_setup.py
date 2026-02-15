import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> None:
    Path("logs").mkdir(exist_ok=True)

    log_level = (os.getenv("LOG_LEVEL", "INFO") or "INFO").upper()
    max_mb = int(os.getenv("LOG_MAX_MB", "10") or "10")
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5") or "5")

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=max_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Reduce noisy per-update logs; keep warnings/errors.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
