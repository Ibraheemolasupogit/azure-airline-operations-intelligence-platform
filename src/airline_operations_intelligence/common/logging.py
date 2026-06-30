"""Logging helpers for local tools and future platform components."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure deterministic console logging for local commands."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
