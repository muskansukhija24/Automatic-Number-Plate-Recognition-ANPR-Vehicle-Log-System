"""
Centralized logging configuration for ANPR & Vehicle Log System.
Provides formatted rotating file logging and console output.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str = "anpr",
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    max_bytes: int = 2 * 1024 * 1024,  # 2 MB per log file
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configure and return a centralized logger with both rotating file and console handlers.

    Args:
        name: Logger hierarchy name.
        log_file: Path to log file. Defaults to 'logs/app.log' relative to project root.
        level: Minimum log severity level (default INFO).
        max_bytes: Maximum size per log file before rotation.
        backup_count: Number of rotated backup log files to retain.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logger is invoked multiple times
    if logger.handlers:
        return logger

    # Ensure log directory exists
    if log_file is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(project_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")
    else:
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    # Common formatter with ISO timestamp, severity level, module, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s.%(funcName)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating File Handler
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        print(f"Warning: Could not create RotatingFileHandler at {log_file}: {exc}")

    # Console Handler (clean format for terminal users)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


# Default application-wide logger
logger = setup_logger()
