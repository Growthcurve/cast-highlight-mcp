"""Observability package for structured logging and metrics.

This package provides unified observability capabilities for the
cast-highlight-mcp server, including:

- Request context management using contextvars for async-safe correlation
- Structured JSON logging with request correlation (Phase 2)
- Metrics collection and export (Phase 3)

Phase 1 exports (context management):
    from cast_highlight_mcp.observability import (
        request_context,
        get_request_id,
        get_current_context,
        RequestContext,
    )

    with request_context(tool_name="highlight_get_company") as ctx:
        # All logging within this block shares the same request_id
        logger.info("Tool call started")
        # ... do work ...
        duration = ctx.elapsed_ms()
"""

from cast_highlight_mcp.observability.context import (
    RequestContext,
    get_current_context,
    get_request_id,
    request_context,
)
from cast_highlight_mcp.observability.logging import (
    ContextAwareLogger,
    LogContext,
    ObservabilityConfig,
    RedactionFilter,
    StructuredLogFormatter,
    TextLogFormatter,
    configure_logging,
    get_logger,
)
from cast_highlight_mcp.observability.metrics import (
    LATENCY_BUCKETS_MS,
    HttpMetrics,
    MetricsCollector,
    ObservabilityState,
    ToolMetrics,
    calculate_percentile,
    get_metrics_collector,
    reset_metrics_collector,
)

__all__ = [
    # Context management (Phase 1)
    "RequestContext",
    "request_context",
    "get_request_id",
    "get_current_context",
    # Logging (Phase 2)
    "configure_logging",
    "get_logger",
    "ContextAwareLogger",
    "LogContext",
    "ObservabilityConfig",
    "RedactionFilter",
    "StructuredLogFormatter",
    "TextLogFormatter",
    # Metrics collection (Phase 3)
    "LATENCY_BUCKETS_MS",
    "HttpMetrics",
    "MetricsCollector",
    "ObservabilityState",
    "ToolMetrics",
    "calculate_percentile",
    "get_metrics_collector",
    "reset_metrics_collector",
]
