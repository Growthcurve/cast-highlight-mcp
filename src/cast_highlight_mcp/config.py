"""Configuration for CAST Highlight MCP Server."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """CAST Highlight API configuration."""

    base_url: str
    access_token: str
    company_id: int
    timeout: int = 30
    retry_attempts: int = 3
    retry_min_wait: float = 1.0
    retry_max_wait: float = 10.0
    retry_multiplier: float = 2.0


@dataclass
class ObservabilityConfig:
    """Observability configuration for logging and metrics.

    Attributes:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format, either "json" for structured logging or "text"
            for human-readable format.
        log_file: Optional file path for log output. If None, logs only to stderr.
        log_redact_ids: Whether to redact company/application IDs in logs.
        metrics_enabled: Whether to enable metrics collection.
        metrics_prefix: Prefix for metric names (e.g., "highlight" -> "highlight_tool_calls_total").
        metrics_detailed: Whether to include per-endpoint metrics (higher cardinality).
    """

    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str | None = None
    log_redact_ids: bool = False
    metrics_enabled: bool = True
    metrics_prefix: str = "highlight"
    metrics_detailed: bool = False


# Valid log levels for validation
_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

# Alternative log level names that should be normalized
_LOG_LEVEL_ALIASES = {
    "WARN": "WARNING",
}


def _parse_bool(value: str | None) -> bool:
    """Parse a boolean value from environment variable string.

    Args:
        value: String value from environment variable, or None.

    Returns:
        True for "true", "1", "yes", "on" (case-insensitive).
        False for everything else including None and empty string.
    """
    if value is None:
        return False
    return value.lower() in ("true", "1", "yes", "on")


def _validate_log_level(level: str) -> str:
    """Validate and normalize a log level string.

    Args:
        level: Log level string from environment.

    Returns:
        Normalized uppercase log level. Defaults to "INFO" if invalid.
    """
    level_upper = level.upper()

    # Handle common aliases
    if level_upper in _LOG_LEVEL_ALIASES:
        level_upper = _LOG_LEVEL_ALIASES[level_upper]

    # Validate against known levels
    if level_upper in _VALID_LOG_LEVELS:
        return level_upper

    # Invalid level - log warning to stderr and use default
    print(
        f"WARNING: Invalid log level '{level}', defaulting to INFO",
        file=sys.stderr,
    )
    return "INFO"


def _validate_log_format(fmt: str) -> str:
    """Validate log format string.

    Args:
        fmt: Log format string from environment.

    Returns:
        Normalized lowercase format. Defaults to "json" if invalid.
    """
    fmt_lower = fmt.lower()
    if fmt_lower in ("json", "text"):
        return fmt_lower

    # Invalid format - log warning to stderr and use default
    print(
        f"WARNING: Invalid log format '{fmt}', defaulting to json",
        file=sys.stderr,
    )
    return "json"


def load_observability_config() -> ObservabilityConfig:
    """Load observability configuration from environment variables.

    Environment Variables:
        HIGHLIGHT_LOG_LEVEL: Minimum log level (default: INFO)
        HIGHLIGHT_LOG_FORMAT: Output format, "json" or "text" (default: json)
        HIGHLIGHT_LOG_FILE: Optional file path for log output
        HIGHLIGHT_LOG_REDACT_IDS: Whether to redact IDs (default: false)
        HIGHLIGHT_METRICS_ENABLED: Enable metrics collection (default: true)
        HIGHLIGHT_METRICS_PREFIX: Metric name prefix (default: highlight)
        HIGHLIGHT_METRICS_DETAILED: Include per-endpoint metrics (default: false)

    Returns:
        ObservabilityConfig with validated settings.
    """
    # Note: load_dotenv() should be called by load_config() first,
    # but we call it here too for standalone use
    load_dotenv()

    # Parse and validate log level
    log_level_raw = os.getenv("HIGHLIGHT_LOG_LEVEL", "INFO")
    log_level = _validate_log_level(log_level_raw)

    # Parse and validate log format
    log_format_raw = os.getenv("HIGHLIGHT_LOG_FORMAT", "json")
    log_format = _validate_log_format(log_format_raw)

    # Parse optional log file path
    log_file = os.getenv("HIGHLIGHT_LOG_FILE")
    # Convert empty string to None
    if log_file == "":
        log_file = None

    # Parse boolean settings
    log_redact_ids = _parse_bool(os.getenv("HIGHLIGHT_LOG_REDACT_IDS"))
    metrics_enabled = _parse_bool(os.getenv("HIGHLIGHT_METRICS_ENABLED", "true"))
    metrics_detailed = _parse_bool(os.getenv("HIGHLIGHT_METRICS_DETAILED"))

    # Parse string settings
    metrics_prefix = os.getenv("HIGHLIGHT_METRICS_PREFIX", "highlight")

    return ObservabilityConfig(
        log_level=log_level,
        log_format=log_format,
        log_file=log_file,
        log_redact_ids=log_redact_ids,
        metrics_enabled=metrics_enabled,
        metrics_prefix=metrics_prefix,
        metrics_detailed=metrics_detailed,
    )


def load_config() -> Config:
    """Load configuration from environment variables.

    Environment Variables:
        HIGHLIGHT_BASE_URL: Base URL for the CAST Highlight API (required)
        HIGHLIGHT_ACCESS_TOKEN: Bearer token for authentication (required)
        HIGHLIGHT_COMPANY_ID: Default company ID (required)
        HIGHLIGHT_TIMEOUT: Request timeout in seconds (default: 30)
        HIGHLIGHT_RETRY_ATTEMPTS: Maximum retry attempts (default: 3)
        HIGHLIGHT_RETRY_MIN_WAIT: Minimum wait between retries in seconds (default: 1.0)
        HIGHLIGHT_RETRY_MAX_WAIT: Maximum wait between retries in seconds (default: 10.0)
        HIGHLIGHT_RETRY_MULTIPLIER: Exponential backoff multiplier (default: 2.0)
    """
    load_dotenv()

    base_url = os.getenv("HIGHLIGHT_BASE_URL")
    access_token = os.getenv("HIGHLIGHT_ACCESS_TOKEN")
    company_id = os.getenv("HIGHLIGHT_COMPANY_ID")
    timeout = int(os.getenv("HIGHLIGHT_TIMEOUT", "30"))

    # Retry configuration
    retry_attempts = int(os.getenv("HIGHLIGHT_RETRY_ATTEMPTS", "3"))
    retry_min_wait = float(os.getenv("HIGHLIGHT_RETRY_MIN_WAIT", "1.0"))
    retry_max_wait = float(os.getenv("HIGHLIGHT_RETRY_MAX_WAIT", "10.0"))
    retry_multiplier = float(os.getenv("HIGHLIGHT_RETRY_MULTIPLIER", "2.0"))

    if not base_url:
        raise ValueError("HIGHLIGHT_BASE_URL environment variable is required")
    if not access_token:
        raise ValueError("HIGHLIGHT_ACCESS_TOKEN environment variable is required")
    if not company_id:
        raise ValueError("HIGHLIGHT_COMPANY_ID environment variable is required")

    return Config(
        base_url=base_url,
        access_token=access_token,
        company_id=int(company_id),
        timeout=timeout,
        retry_attempts=retry_attempts,
        retry_min_wait=retry_min_wait,
        retry_max_wait=retry_max_wait,
        retry_multiplier=retry_multiplier,
    )
