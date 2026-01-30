"""Structured logging module for cast-highlight-mcp.

This module provides:
- StructuredLogFormatter: JSON output format for machine parsing
- TextLogFormatter: Human-readable output format
- RedactionFilter: Sensitive data redaction
- configure_logging(): Configure logging based on settings
- get_logger(): Get a context-aware logger for a module

All logging operations are designed for graceful degradation - logging
failures will never raise exceptions or impact tool functionality.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import sys
import traceback
from dataclasses import dataclass, field, fields
from typing import Any

# Sensitive patterns for redaction
_SENSITIVE_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_\.]+"), "Bearer [REDACTED]"),
    (
        re.compile(r'access_token["\']?\s*[:=]\s*["\']?[^"\'&\s]+'),
        "access_token=[REDACTED]",
    ),
    (
        re.compile(r'Authorization["\']?\s*[:=]\s*["\']?[^"\'&\s]+'),
        "Authorization=[REDACTED]",
    ),
    (
        re.compile(r'token["\']?\s*[:=]\s*["\']?[A-Za-z0-9\-_\.]{20,}'),
        "token=[REDACTED]",
    ),
]

# Sensitive keys (case-insensitive)
_SENSITIVE_KEYS = frozenset(
    [
        "access_token",
        "authorization",
        "token",
        "api_key",
        "apikey",
        "secret",
        "password",
        "credential",
    ]
)

# ID fields that can be optionally redacted
_ID_FIELDS = frozenset(["company_id", "domain_id", "application_id", "app_id"])


@dataclass
class LogContext:
    """Structured context for log entries.

    Attributes:
        request_id: Unique identifier for request correlation
        tool_name: MCP tool being invoked
        duration_ms: Operation duration in milliseconds
        success: Whether operation succeeded
        error_type: Exception class name if error
        error_message: Error description if error
        http_method: HTTP method (GET, POST, etc.)
        http_path: URL path (not full URL)
        http_status: HTTP response status code
        response_size_bytes: Response payload size
        extra: Additional context fields
    """

    request_id: str
    tool_name: str | None = None
    duration_ms: float | None = None
    success: bool | None = None
    error_type: str | None = None
    error_message: str | None = None
    http_method: str | None = None
    http_path: str | None = None
    http_status: int | None = None
    response_size_bytes: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value is not None:
                if f.name == "extra":
                    # Merge extra dict into result
                    result.update(value)
                else:
                    result[f.name] = value
        return result


@dataclass
class ObservabilityConfig:
    """Configuration for logging behavior.

    Attributes:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "text")
        log_file: Optional file path for log output
        log_redact_ids: Whether to redact company/app IDs
    """

    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str | None = None
    log_redact_ids: bool = False

    @classmethod
    def from_env(cls) -> ObservabilityConfig:
        """Load configuration from environment variables."""
        return cls(
            log_level=os.getenv("HIGHLIGHT_LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("HIGHLIGHT_LOG_FORMAT", "json").lower(),
            log_file=os.getenv("HIGHLIGHT_LOG_FILE"),
            log_redact_ids=os.getenv("HIGHLIGHT_LOG_REDACT_IDS", "false").lower()
            in ("true", "1", "yes", "on"),
        )

    def validate(self) -> None:
        """Validate configuration values, using defaults for invalid values."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_levels:
            # Log warning to stderr since logging may not be configured yet
            sys.stderr.write(f"Warning: Invalid log level '{self.log_level}', defaulting to INFO\n")
            self.log_level = "INFO"

        valid_formats = {"json", "text"}
        if self.log_format not in valid_formats:
            sys.stderr.write(
                f"Warning: Invalid log format '{self.log_format}', defaulting to json\n"
            )
            self.log_format = "json"


class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Produces log entries in the format:
    {
        "timestamp": "2026-01-29T12:34:56.789Z",
        "level": "INFO",
        "logger": "cast_highlight_mcp.server",
        "message": "Tool call completed",
        "context": {...}
    }
    """

    TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, redact_ids: bool = False) -> None:
        """Initialize formatter.

        Args:
            redact_ids: Whether to redact company/app IDs in output
        """
        super().__init__()
        self.redact_ids = redact_ids

    def format(self, record: logging.LogRecord) -> str:
        """Convert log record to JSON string.

        Args:
            record: Python logging LogRecord object

        Returns:
            JSON-formatted string
        """
        try:
            entry = {
                "timestamp": self._format_timestamp(record.created),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }

            # Add context if present
            context = getattr(record, "context", None)
            if context is not None:
                if isinstance(context, LogContext):
                    context = context.to_dict()
                elif isinstance(context, dict):
                    context = context.copy()
                else:
                    context = {}

                # Apply ID redaction if configured
                if self.redact_ids:
                    context = self._redact_ids(context)

                if context:  # Only add non-empty context
                    entry["context"] = context

            # Add exception info if present
            if record.exc_info is not None and record.exc_info[0] is not None:
                entry["exception"] = self._format_exception(record.exc_info)

            return json.dumps(entry, default=str, ensure_ascii=False)

        except (TypeError, ValueError, RecursionError, RuntimeError) as e:
            # Fallback for serialization errors (including when default=str raises)
            return self._fallback_format(record, e)
        except Exception as e:
            # Catch-all for any other unexpected errors
            return self._fallback_format(record, e)

    def _format_timestamp(self, created: float) -> str:
        """Convert Unix timestamp to ISO 8601 format with milliseconds.

        Args:
            created: Unix timestamp from LogRecord

        Returns:
            ISO 8601 formatted string (e.g., "2026-01-29T12:34:56.789Z")
        """
        dt = datetime.datetime.fromtimestamp(created, tz=datetime.timezone.utc)
        base = dt.strftime(self.TIMESTAMP_FORMAT)
        ms = int((created % 1) * 1000)
        return f"{base}.{ms:03d}Z"

    def _format_exception(self, exc_info: tuple) -> dict:
        """Format exception information for JSON output.

        Args:
            exc_info: (type, value, traceback) tuple

        Returns:
            Dictionary with exception details
        """
        if exc_info is None or exc_info[0] is None:
            return {}

        exc_type, exc_value, exc_tb = exc_info
        return {
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": traceback.format_exception(exc_type, exc_value, exc_tb),
        }

    def _redact_ids(self, context: dict) -> dict:
        """Redact ID fields from context dictionary.

        Args:
            context: Original context dictionary

        Returns:
            Context with IDs redacted
        """
        redacted = context.copy()

        for field_name in _ID_FIELDS:
            if field_name in redacted:
                redacted[field_name] = "[REDACTED_ID]"

        # Handle nested arguments
        if "arguments" in redacted and isinstance(redacted["arguments"], dict):
            redacted["arguments"] = self._redact_ids(redacted["arguments"])

        return redacted

    def _fallback_format(self, record: logging.LogRecord, error: Exception) -> str:
        """Create fallback log entry when normal formatting fails.

        Args:
            record: The log record
            error: The exception that caused the failure

        Returns:
            Minimal valid JSON string
        """
        fallback = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": f"[Log serialization failed: {error}] {str(record.msg)[:200]}",
        }
        return json.dumps(fallback)


class TextLogFormatter(logging.Formatter):
    """Human-readable text formatter for logs.

    Produces log entries in the format:
    2026-01-29 12:34:56.789 INFO  [logger.name] Message key=value key=value
    """

    def __init__(self, redact_ids: bool = False) -> None:
        """Initialize formatter.

        Args:
            redact_ids: Whether to redact company/app IDs in output
        """
        super().__init__()
        self.redact_ids = redact_ids

    def format(self, record: logging.LogRecord) -> str:
        """Convert log record to human-readable text.

        Args:
            record: Python logging LogRecord object

        Returns:
            Formatted text string
        """
        try:
            timestamp = self._format_timestamp(record.created)
            level = f"{record.levelname:<5}"  # Left-align, pad to 5 chars
            logger_name = record.name

            # Build base message
            parts = [timestamp, level, f"[{logger_name}]", record.getMessage()]

            # Append context fields as key=value pairs
            context = getattr(record, "context", None)
            if context is not None:
                if isinstance(context, LogContext):
                    context = context.to_dict()
                elif isinstance(context, dict):
                    context = context.copy()
                else:
                    context = {}

                if self.redact_ids:
                    context = self._redact_ids(context)

                for key, value in context.items():
                    formatted_value = self._format_value(value)
                    parts.append(f"{key}={formatted_value}")

            return " ".join(parts)

        except Exception:
            # Fallback for any formatting errors
            return f"{record.levelname} {record.name} {record.getMessage()}"

    def _format_timestamp(self, created: float) -> str:
        """Format timestamp for text output.

        Args:
            created: Unix timestamp

        Returns:
            Formatted timestamp string (e.g., "2026-01-29 12:34:56.789")
        """
        dt = datetime.datetime.fromtimestamp(created, tz=datetime.timezone.utc)
        base = dt.strftime("%Y-%m-%d %H:%M:%S")
        ms = int((created % 1) * 1000)
        return f"{base}.{ms:03d}"

    def _format_value(self, value: Any) -> str:
        """Format a value for text output.

        Args:
            value: The value to format

        Returns:
            Formatted string representation
        """
        if isinstance(value, str):
            return value
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, float):
            return f"{value:.2f}"
        else:
            return str(value)

    def _redact_ids(self, context: dict) -> dict:
        """Redact ID fields from context dictionary.

        Args:
            context: Original context dictionary

        Returns:
            Context with IDs redacted
        """
        redacted = context.copy()

        for field_name in _ID_FIELDS:
            if field_name in redacted:
                redacted[field_name] = "[REDACTED_ID]"

        return redacted


class RedactionFilter(logging.Filter):
    """Filter that redacts sensitive data from all log records.

    This filter transforms log records to remove sensitive information
    like access tokens, API keys, and passwords. It always returns True
    (allows all records through) as its purpose is transformation, not
    filtering.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Apply redaction to log record.

        Args:
            record: LogRecord to process

        Returns:
            True (always allows records through)
        """
        try:
            # Redact message string
            if isinstance(record.msg, str):
                record.msg = self._redact_string(record.msg)

            # Redact arguments if present
            if record.args:
                if isinstance(record.args, dict):
                    record.args = self._redact_dict(record.args)
                elif isinstance(record.args, tuple):
                    record.args = tuple(self._redact_value(arg) for arg in record.args)

            # Redact context if present
            if hasattr(record, "context"):
                if isinstance(record.context, dict):
                    record.context = self._redact_dict(record.context)
                elif isinstance(record.context, LogContext):
                    record.context.extra = self._redact_dict(record.context.extra)

        except Exception:
            # Graceful degradation - don't let redaction failures break logging
            pass

        return True  # Always allow record through

    def _redact_string(self, value: str) -> str:
        """Apply regex patterns to redact sensitive data in strings.

        Args:
            value: String to redact

        Returns:
            Redacted string
        """
        if not isinstance(value, str):
            return value

        result = value
        for pattern, replacement in _SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)

        return result

    def _redact_dict(self, data: dict) -> dict:
        """Recursively redact sensitive keys in dictionaries.

        Args:
            data: Dictionary to redact

        Returns:
            Redacted dictionary (new copy)
        """
        result = {}

        for key, value in data.items():
            key_lower = key.lower()

            if key_lower in _SENSITIVE_KEYS:
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = [self._redact_value(item) for item in value]
            elif isinstance(value, str):
                result[key] = self._redact_string(value)
            else:
                result[key] = value

        return result

    def _redact_value(self, value: Any) -> Any:
        """Redact a single value based on its type.

        Args:
            value: Any value

        Returns:
            Redacted value
        """
        if isinstance(value, dict):
            return self._redact_dict(value)
        elif isinstance(value, str):
            return self._redact_string(value)
        elif isinstance(value, list):
            return [self._redact_value(item) for item in value]
        else:
            return value


class ContextAwareLogger(logging.LoggerAdapter):
    """Logger adapter that adds context to log records.

    This adapter wraps a standard logger and automatically injects
    context information into log records via the 'extra' mechanism.
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Add context to log record.

        Args:
            msg: Log message
            kwargs: Additional log arguments

        Returns:
            Processed (msg, kwargs) tuple
        """
        # Ensure extra dict exists
        extra = kwargs.get("extra", {})

        # Merge any provided context
        if "context" not in extra:
            extra["context"] = {}

        kwargs["extra"] = extra
        return msg, kwargs


def configure_logging(config: ObservabilityConfig | None = None) -> None:
    """Configure the logging system based on settings.

    Args:
        config: ObservabilityConfig instance (loads from env if None)
    """
    # Load config from environment if not provided
    if config is None:
        config = ObservabilityConfig.from_env()

    # Validate configuration
    config.validate()

    # Get root logger for cast_highlight_mcp package
    root_logger = logging.getLogger("cast_highlight_mcp")

    # Clear existing handlers to prevent duplicates
    root_logger.handlers.clear()

    # Set log level
    level = getattr(logging, config.log_level)
    root_logger.setLevel(level)

    # Create formatter based on config
    if config.log_format == "json":
        formatter = StructuredLogFormatter(redact_ids=config.log_redact_ids)
    else:
        formatter = TextLogFormatter(redact_ids=config.log_redact_ids)

    # Create console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Add redaction filter to console handler
    redaction_filter = RedactionFilter()
    console_handler.addFilter(redaction_filter)

    root_logger.addHandler(console_handler)

    # Add file handler if configured
    if config.log_file:
        try:
            file_handler = logging.FileHandler(
                config.log_file,
                mode="a",  # Append mode
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            file_handler.addFilter(redaction_filter)
            root_logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            # Log to stderr but don't fail
            sys.stderr.write(f"Warning: Could not open log file '{config.log_file}': {e}\n")

    # Prevent propagation to root logger to avoid duplicate logs
    root_logger.propagate = False

    # Log configuration complete (at DEBUG level to avoid noise)
    root_logger.debug(
        "Logging configured",
        extra={
            "context": {
                "log_level": config.log_level,
                "log_format": config.log_format,
                "log_file": config.log_file or "(none)",
            }
        },
    )


def get_logger(name: str) -> ContextAwareLogger:
    """Get a context-aware logger for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        ContextAwareLogger wrapping the standard logger
    """
    base_logger = logging.getLogger(name)
    return ContextAwareLogger(base_logger, {})
