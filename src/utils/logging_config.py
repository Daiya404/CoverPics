# ==============================================================================
# FILE: src/utils/logging_config.py
# ==============================================================================

import logging
import sys
from pathlib import Path

# --- Constants ---
# By defining the logger name as a constant, we ensure that all other
# modules can access the same logger instance using logging.getLogger(LOGGER_NAME).
LOGGER_NAME = "poster_downloader"
LOG_DIR = Path("logs") # The standard logging directory for the project.

def setup_logging(log_level: str = "INFO") -> None:
    """
    Configures the application's root logger for dual output.

    This function should be called ONLY ONCE at the beginning of the
    application's lifecycle (e.g., in main.py). It sets up a logger that
    sends messages to both a file (`logs/downloader.log`) and the console.

    The configuration is idempotent; calling it multiple times will not
    result in duplicate log handlers or messages.

    Args:
        log_level: The minimum logging level to process (e.g., "DEBUG", "INFO").
                   Defaults to "INFO".
    """
    # 1. Ensure the log directory exists.
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file_path = LOG_DIR / "downloader.log"

    # 2. Get the logger instance.
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(log_level.upper())

    # 3. Clear any existing handlers to prevent duplication.
    # This makes the function safe to call more than once, if necessary.
    if logger.hasHandlers():
        logger.handlers.clear()

    # 4. Define a consistent format for log messages.
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)-8s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 5. Create a handler to write logs to a file.
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 6. Create a handler to stream logs to the console.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("=" * 60)
    logger.info(f"Logging initialized with level {log_level.upper()}. Outputting to {log_file_path}")
    logger.info("=" * 60)