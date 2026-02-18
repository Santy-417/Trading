import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """Configure standard logging with uvicorn-style format."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(levelname)-9s %(message)s",
        stream=sys.stdout,
    )

    # Suppress noisy third-party loggers
    for logger_name in ("sqlalchemy.engine",):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)
