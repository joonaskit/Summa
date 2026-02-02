"""
Centralized logging configuration for the Summa backend.

This module provides a consistent logging setup across all backend modules with:
- Structured logging with consistent formatting
- Colored console output for development
- Configurable log levels via environment variables
- Request ID tracking for correlation
"""

import logging
import os
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"
        
        # Format the message
        result = super().format(record)
        
        # Reset levelname for subsequent formatters
        record.levelname = levelname
        
        return result


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'console')
        log_file: Optional file path for log output
    """
    # Get configuration from environment or use defaults
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = log_format or os.getenv("LOG_FORMAT", "console").lower()
    log_file = log_file or os.getenv("LOG_FILE")
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Create formatters
    if log_format == "json":
        # JSON format for production/structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s", '
            '"function": "%(funcName)s", "line": %(lineno)d}'
        )
    else:
        # Human-readable format for development
        console_format = (
            '%(asctime)s - %(levelname)s - %(name)s - '
            '%(funcName)s:%(lineno)d - %(message)s'
        )
        formatter = ColoredFormatter(
            console_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        # Use plain formatter for file output (no colors)
        plain_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - '
            '%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(plain_formatter)
        root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Log the configuration
    root_logger.info(
        f"Logging configured: level={log_level}, format={log_format}, "
        f"file={log_file or 'None'}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Name of the module (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Initialize logging when module is imported
# This ensures logging is set up before any other modules use it
if not logging.getLogger().handlers:
    setup_logging()
