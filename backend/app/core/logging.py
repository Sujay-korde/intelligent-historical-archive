import logging
import sys
from typing import Any, Dict


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured, clean console logging for the application."""
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger config
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Suppress overly noisy loggers in third party libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger("archive_app")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


logger = setup_logging()
