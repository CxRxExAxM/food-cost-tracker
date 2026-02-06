"""
Centralized logging configuration.

Usage:
    from ..logger import get_logger
    logger = get_logger(__name__)

    logger.info("Something happened")
    logger.error("Something failed", exc_info=True)
    logger.debug("Debug info")  # Only shows if LOG_LEVEL=DEBUG
"""
import logging
import os

# Get log level from environment, default to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given module name.

    Args:
        name: Usually __name__ from the calling module

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
