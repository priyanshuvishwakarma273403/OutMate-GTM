"""Centralized structured logging setup with secret sanitization."""

import logging
import re
import sys

# Sensitive patterns that should never appear in plain text logs
SENSITIVE_PATTERNS = [
    re.compile(
        r"(api[_-]?key|secret|token|authorization|password)[\"']?\s*[:=]\s*[\"']?([^\"'\s]+)",
        re.IGNORECASE,
    ),
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]+)", re.IGNORECASE),
]


class SecretSanitizingFormatter(logging.Formatter):
    """Custom logging formatter that scrubs API keys and bearer tokens from logs."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(r"\1: [REDACTED]", sanitized)
        return sanitized


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root and application loggers with secure formatting."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = SecretSanitizingFormatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    logger = logging.getLogger("outmate")
    logger.setLevel(level)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a scoped logger under the outmate namespace."""
    return logging.getLogger(f"outmate.{name}")
