"""Logging configuration for OqeeRewind."""

import logging
import sys

class ColoredFormatter(logging.Formatter):
    """Custom logging formatter to add colors to log levels."""

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    green = "\x1b[32;20m"
    cyan = "\x1b[36;20m"

    FORMATS = {
        logging.DEBUG: cyan + "%(levelname)s" + reset + " - %(message)s",
        logging.INFO: green + "%(levelname)s" + reset + " - %(message)s",
        logging.WARNING: yellow + "%(levelname)s" + reset + " - %(message)s",
        logging.ERROR: red + "%(levelname)s" + reset + " - %(message)s",
        logging.CRITICAL: bold_red + "%(levelname)s" + reset + " - %(message)s"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    log = logging.getLogger("OqeeRewind")
    log.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    formatter = ColoredFormatter()
    console_handler.setFormatter(formatter)

    # Add handler to logger
    if not log.handlers:
        log.addHandler(console_handler)

    return log

# Create a default logger instance
logger = logging.getLogger("OqeeRewind")
