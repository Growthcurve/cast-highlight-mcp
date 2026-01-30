"""Metrics collection module for the cast-highlight-mcp server.

This module provides thread-safe metrics collection for tool calls and HTTP
requests. It supports JSON and Prometheus export formats.

Key features:
- Thread-safe with threading.Lock
- Histogram buckets for latency distribution
- Percentile calculation (p50, p90, p95, p99)
- Graceful degradation (metrics failures don't raise exceptions)
- No external dependencies (stdlib only)
"""

from __future__ import annotations

import json
import math
import sys
import threading
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Histogram bucket boundaries in milliseconds
# Covers range from 10ms to 10s for typical API latencies
LATENCY_BUCKETS_MS: tuple[int | float, ...] = (
    10,
    25,
    50,
    100,
    250,
    500,
    1000,
    2500,
    5000,
    10000,
    float("inf"),
)


def _initialize_buckets() -> dict[int | float, int]:
    """Initialize histogram buckets with zero counts."""
    return {bucket: 0 for bucket in LATENCY_BUCKETS_MS}


@dataclass
class ToolMetrics:
    """Metrics for a single MCP tool.

    Attributes:
        tool_name: The tool identifier (e.g., "highlight_get_company")
        calls_total: Total number of invocations (success + error)
        calls_success: Number of successful completions
        calls_error: Number of failed invocations
        latency_sum_ms: Sum of all latencies in milliseconds
        latency_buckets: Histogram buckets for latency distribution
        latency_values: Raw latency values for percentile calculation
        errors_by_type: Error counts by category
        last_call_timestamp: Unix timestamp of most recent call
    """

    tool_name: str
    calls_total: int = 0
    calls_success: int = 0
    calls_error: int = 0
    latency_sum_ms: float = 0.0
    latency_buckets: dict[int | float, int] = field(default_factory=_initialize_buckets)
    latency_values: list[float] = field(default_factory=list)
    errors_by_type: dict[str, int] = field(default_factory=dict)
    last_call_timestamp: float | None = None


@dataclass
class HttpMetrics:
    """Metrics for HTTP client requests to CAST Highlight API.

    Attributes:
        requests_total: Total HTTP requests made
        requests_by_status: Status code counts
        requests_by_method: Method counts (GET, POST, etc.)
        latency_sum_ms: Sum of HTTP request latencies
        latency_buckets: Histogram buckets for latency distribution
        latency_values: Raw values for percentile calculation
        errors_total: Total HTTP errors (4xx + 5xx + connection failures)
    """

    requests_total: int = 0
    requests_by_status: dict[int, int] = field(default_factory=dict)
    requests_by_method: dict[str, int] = field(default_factory=dict)
    latency_sum_ms: float = 0.0
    latency_buckets: dict[int | float, int] = field(default_factory=_initialize_buckets)
    latency_values: list[float] = field(default_factory=list)
    errors_total: int = 0


@dataclass
class ObservabilityState:
    """Global container for all observability metrics.

    Attributes:
        start_time: Unix timestamp when metrics collection started
        tools: Tool name -> ToolMetrics mapping
        http: HTTP client metrics
        reset_count: Number of times metrics have been reset
        last_reset_time: Timestamp of last reset
    """

    start_time: float = field(default_factory=time.time)
    tools: dict[str, ToolMetrics] = field(default_factory=dict)
    http: HttpMetrics = field(default_factory=HttpMetrics)
    reset_count: int = 0
    last_reset_time: float | None = None


def calculate_percentile(samples: list[float], percentile: float) -> float:
    """Calculate a specific percentile from latency samples.

    Uses linear interpolation between adjacent values for non-integer indices.

    Args:
        samples: List of latency values
        percentile: Desired percentile (0-100, e.g., 50, 95, 99)

    Returns:
        Percentile value, or 0.0 if no samples
    """
    if not samples:
        return 0.0

    sorted_samples = sorted(samples)
    n = len(sorted_samples)

    if n == 1:
        return sorted_samples[0]

    # Calculate index using linear interpolation
    # percentile/100 gives the fractional position (0.0 to 1.0)
    # Multiply by (n-1) to get the index in 0-based array
    index = (percentile / 100.0) * (n - 1)

    lower_index = int(math.floor(index))
    upper_index = int(math.ceil(index))

    # Clamp to valid range
    lower_index = max(0, min(lower_index, n - 1))
    upper_index = max(0, min(upper_index, n - 1))

    # If index is exact integer, return that value
    if lower_index == upper_index:
        return sorted_samples[lower_index]

    # Linear interpolation between adjacent values
    fraction = index - lower_index
    lower_value = sorted_samples[lower_index]
    upper_value = sorted_samples[upper_index]

    return lower_value + (fraction * (upper_value - lower_value))


def _calculate_percentiles(
    latency_values: list[float],
) -> dict[str, float]:
    """Get standard percentiles (p50, p90, p95, p99) for a latency list.

    Args:
        latency_values: Raw latency samples

    Returns:
        Dictionary with percentile names and values
    """
    return {
        "p50_ms": round(calculate_percentile(latency_values, 50), 2),
        "p90_ms": round(calculate_percentile(latency_values, 90), 2),
        "p95_ms": round(calculate_percentile(latency_values, 95), 2),
        "p99_ms": round(calculate_percentile(latency_values, 99), 2),
    }


class MetricsCollector:
    """Thread-safe metrics collection and export.

    This class collects metrics for tool calls and HTTP requests, storing
    them in a thread-safe manner. Metrics can be exported in JSON or
    Prometheus format.

    Attributes:
        _state: The metrics state container
        _lock: Lock for thread-safe counter operations
        _enabled: Whether metrics collection is enabled
        _prefix: Metric name prefix for export
        _max_latency_samples: Maximum latency samples to retain per metric
    """

    def __init__(
        self,
        enabled: bool = True,
        prefix: str = "highlight",
    ) -> None:
        """Initialize the MetricsCollector.

        Args:
            enabled: Whether metrics collection is enabled
            prefix: Metric name prefix for Prometheus export
        """
        self._state = ObservabilityState()
        self._lock = threading.Lock()
        self._enabled = enabled
        self._prefix = prefix
        self._max_latency_samples = 10000

    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        """Record metrics for a completed tool invocation.

        This method is thread-safe and will not raise exceptions.
        Metrics recording failures are silently logged to stderr.

        Args:
            tool_name: Name of the tool (e.g., "highlight_get_company")
            duration_ms: Call duration in milliseconds
            success: Whether the call succeeded
            error_type: Error category if failed (optional)
        """
        if not self._enabled:
            return

        try:
            current_time = time.time()

            with self._lock:
                # Get or create tool metrics
                if tool_name not in self._state.tools:
                    self._state.tools[tool_name] = ToolMetrics(tool_name=tool_name)

                metrics = self._state.tools[tool_name]

                # Increment counters
                metrics.calls_total += 1

                if success:
                    metrics.calls_success += 1
                else:
                    metrics.calls_error += 1

                    # Record error type
                    if error_type:
                        if error_type not in metrics.errors_by_type:
                            metrics.errors_by_type[error_type] = 0
                        metrics.errors_by_type[error_type] += 1

                # Record latency
                metrics.latency_sum_ms += duration_ms
                self._update_histogram_bucket(metrics.latency_buckets, duration_ms)
                self._append_latency_sample(metrics.latency_values, duration_ms)

                # Update timestamp
                metrics.last_call_timestamp = current_time

        except Exception as e:
            # Graceful degradation - log to stderr but don't raise
            print(f"Metrics recording error: {e}", file=sys.stderr)

    def record_http_request(
        self,
        method: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Record metrics for an HTTP request to CAST Highlight API.

        This method is thread-safe and will not raise exceptions.
        Metrics recording failures are silently logged to stderr.

        Args:
            method: HTTP method (GET, POST, etc.)
            status_code: Response status code (200, 404, 500, etc.)
            duration_ms: Request duration in milliseconds
        """
        if not self._enabled:
            return

        try:
            with self._lock:
                http = self._state.http

                # Increment total counter
                http.requests_total += 1

                # Increment status code counter
                if status_code not in http.requests_by_status:
                    http.requests_by_status[status_code] = 0
                http.requests_by_status[status_code] += 1

                # Increment method counter
                method_upper = method.upper()
                if method_upper not in http.requests_by_method:
                    http.requests_by_method[method_upper] = 0
                http.requests_by_method[method_upper] += 1

                # Track errors (4xx, 5xx)
                if status_code >= 400:
                    http.errors_total += 1

                # Record latency
                http.latency_sum_ms += duration_ms
                self._update_histogram_bucket(http.latency_buckets, duration_ms)
                self._append_latency_sample(http.latency_values, duration_ms)

        except Exception as e:
            print(f"HTTP metrics recording error: {e}", file=sys.stderr)

    def get_metrics(self) -> ObservabilityState:
        """Get current metrics state snapshot.

        Returns a deep copy of the internal state to prevent external
        modification.

        Returns:
            Copy of current ObservabilityState
        """
        with self._lock:
            return deepcopy(self._state)

    def export_json(self) -> str:
        """Export all metrics as a JSON string.

        Returns:
            JSON-formatted metrics string
        """
        with self._lock:
            current_time = time.time()
            uptime_seconds = current_time - self._state.start_time

            # Build tools section
            tools_data: dict[str, Any] = {}
            for tool_name, metrics in self._state.tools.items():
                percentiles = _calculate_percentiles(metrics.latency_values)

                # Calculate average latency
                avg_latency = 0.0
                if metrics.calls_total > 0:
                    avg_latency = metrics.latency_sum_ms / metrics.calls_total

                tools_data[tool_name] = {
                    "calls_total": metrics.calls_total,
                    "calls_success": metrics.calls_success,
                    "calls_error": metrics.calls_error,
                    "latency_avg_ms": round(avg_latency, 2),
                    "latency_p50_ms": percentiles["p50_ms"],
                    "latency_p90_ms": percentiles["p90_ms"],
                    "latency_p95_ms": percentiles["p95_ms"],
                    "latency_p99_ms": percentiles["p99_ms"],
                    "errors_by_type": dict(metrics.errors_by_type),
                    "last_call_timestamp": metrics.last_call_timestamp,
                }

            # Build HTTP section
            http = self._state.http
            http_percentiles = _calculate_percentiles(http.latency_values)

            http_avg_latency = 0.0
            if http.requests_total > 0:
                http_avg_latency = http.latency_sum_ms / http.requests_total

            # Convert status code keys to strings for JSON compatibility
            requests_by_status_str = {str(k): v for k, v in http.requests_by_status.items()}

            http_data = {
                "requests_total": http.requests_total,
                "requests_by_status": requests_by_status_str,
                "requests_by_method": dict(http.requests_by_method),
                "errors_total": http.errors_total,
                "latency_avg_ms": round(http_avg_latency, 2),
                "latency_p50_ms": http_percentiles["p50_ms"],
                "latency_p90_ms": http_percentiles["p90_ms"],
                "latency_p95_ms": http_percentiles["p95_ms"],
                "latency_p99_ms": http_percentiles["p99_ms"],
            }

            # Build complete export structure
            export_data = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "uptime_seconds": round(uptime_seconds, 2),
                "reset_count": self._state.reset_count,
                "last_reset_time": self._state.last_reset_time,
                "tools": tools_data,
                "http": http_data,
            }

        return json.dumps(export_data, indent=2)

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text exposition format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines: list[str] = []
        prefix = self._prefix

        with self._lock:
            # =====================================================
            # Tool Call Metrics
            # =====================================================

            # Tool calls total (counter)
            lines.append(f"# HELP {prefix}_tool_calls_total Total number of tool calls")
            lines.append(f"# TYPE {prefix}_tool_calls_total counter")

            for tool_name, metrics in self._state.tools.items():
                lines.append(
                    f'{prefix}_tool_calls_total{{tool_name="{tool_name}",status="success"}} {metrics.calls_success}'
                )
                lines.append(
                    f'{prefix}_tool_calls_total{{tool_name="{tool_name}",status="error"}} {metrics.calls_error}'
                )
            lines.append("")

            # Tool duration histogram
            lines.append(f"# HELP {prefix}_tool_duration_seconds Tool call duration in seconds")
            lines.append(f"# TYPE {prefix}_tool_duration_seconds histogram")

            for tool_name, metrics in self._state.tools.items():
                # Histogram buckets (convert ms to seconds for Prometheus convention)
                for bucket_ms in sorted(metrics.latency_buckets.keys()):
                    count = metrics.latency_buckets[bucket_ms]
                    if bucket_ms == float("inf"):
                        le = "+Inf"
                    else:
                        le = str(bucket_ms / 1000.0)
                    lines.append(
                        f'{prefix}_tool_duration_seconds_bucket{{tool_name="{tool_name}",le="{le}"}} {count}'
                    )

                # Sum and count
                sum_seconds = metrics.latency_sum_ms / 1000.0
                lines.append(
                    f'{prefix}_tool_duration_seconds_sum{{tool_name="{tool_name}"}} {sum_seconds}'
                )
                lines.append(
                    f'{prefix}_tool_duration_seconds_count{{tool_name="{tool_name}"}} {metrics.calls_total}'
                )
            lines.append("")

            # Tool errors by type (counter)
            lines.append(f"# HELP {prefix}_errors_total Total errors by type")
            lines.append(f"# TYPE {prefix}_errors_total counter")

            for tool_name, metrics in self._state.tools.items():
                for error_type, count in metrics.errors_by_type.items():
                    lines.append(
                        f'{prefix}_errors_total{{tool_name="{tool_name}",error_type="{error_type}"}} {count}'
                    )
            lines.append("")

            # =====================================================
            # HTTP Request Metrics
            # =====================================================

            http = self._state.http

            # HTTP requests total (counter)
            lines.append(f"# HELP {prefix}_http_requests_total Total HTTP requests to CAST API")
            lines.append(f"# TYPE {prefix}_http_requests_total counter")

            for status_code, count in sorted(http.requests_by_status.items()):
                lines.append(
                    f'{prefix}_http_requests_total{{method="GET",status_code="{status_code}"}} {count}'
                )
            lines.append("")

            # HTTP duration histogram
            lines.append(f"# HELP {prefix}_http_duration_seconds HTTP request duration in seconds")
            lines.append(f"# TYPE {prefix}_http_duration_seconds histogram")

            for bucket_ms in sorted(http.latency_buckets.keys()):
                count = http.latency_buckets[bucket_ms]
                if bucket_ms == float("inf"):
                    le = "+Inf"
                else:
                    le = str(bucket_ms / 1000.0)
                lines.append(
                    f'{prefix}_http_duration_seconds_bucket{{method="GET",le="{le}"}} {count}'
                )

            sum_seconds = http.latency_sum_ms / 1000.0
            lines.append(f'{prefix}_http_duration_seconds_sum{{method="GET"}} {sum_seconds}')
            lines.append(
                f'{prefix}_http_duration_seconds_count{{method="GET"}} {http.requests_total}'
            )
            lines.append("")

            # =====================================================
            # Uptime Metric
            # =====================================================

            uptime = time.time() - self._state.start_time
            lines.append(f"# HELP {prefix}_uptime_seconds Server uptime in seconds")
            lines.append(f"# TYPE {prefix}_uptime_seconds gauge")
            lines.append(f"{prefix}_uptime_seconds {uptime}")

        return "\n".join(lines)

    def reset(self, tool_name: str | None = None) -> None:
        """Reset metrics to initial state.

        If tool_name is provided, only that tool's metrics are reset.
        Otherwise, all metrics are reset.

        Args:
            tool_name: Specific tool to reset, or None for all
        """
        with self._lock:
            current_time = time.time()
            self._state.reset_count += 1
            self._state.last_reset_time = current_time

            if tool_name is None:
                # Reset all metrics
                self._state.tools = {}
                self._state.http = HttpMetrics()
                self._state.start_time = current_time
            else:
                # Reset specific tool only
                if tool_name in self._state.tools:
                    self._state.tools[tool_name] = ToolMetrics(tool_name=tool_name)

    def _update_histogram_bucket(
        self,
        buckets: dict[int | float, int],
        value_ms: float,
    ) -> None:
        """Increment the appropriate histogram buckets for a latency value.

        Histogram buckets are cumulative - each bucket counts all observations
        less than or equal to the bucket boundary. This matches Prometheus
        histogram semantics.

        Args:
            buckets: Bucket boundaries -> counts
            value_ms: Latency value in milliseconds
        """
        for boundary in buckets:
            if value_ms <= boundary:
                buckets[boundary] += 1

    def _append_latency_sample(
        self,
        samples: list[float],
        value_ms: float,
    ) -> None:
        """Add latency sample with bounded memory (sliding window).

        Args:
            samples: Existing samples list
            value_ms: New latency value
        """
        samples.append(value_ms)

        # Enforce maximum sample count (sliding window)
        if len(samples) > self._max_latency_samples:
            samples.pop(0)


# Module-level state for singleton pattern
_metrics_collector: MetricsCollector | None = None
_collector_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global MetricsCollector singleton.

    This function is thread-safe and uses double-checked locking pattern.

    Returns:
        The global MetricsCollector instance
    """
    global _metrics_collector

    if _metrics_collector is not None:
        return _metrics_collector

    with _collector_lock:
        # Double-check locking pattern
        if _metrics_collector is None:
            _metrics_collector = MetricsCollector()
        return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector.

    This is primarily intended for testing purposes.
    """
    global _metrics_collector

    with _collector_lock:
        if _metrics_collector is not None:
            _metrics_collector.reset()
