# SPARC Pseudocode: Metrics Module

> **Document Version**: 1.0.0
> **Status**: Draft
> **Related Spec**: OBSERVABILITY-SPEC.md (Sections 2.2, 4.1, 5.2)
> **Author**: SPARC Pseudocode Agent
> **Date**: 2026-01-29

---

## 1. Overview

This document provides detailed pseudocode for the metrics collection module of the
`cast-highlight-mcp` observability system. The module collects tool call and HTTP
request metrics, computes latency percentiles, and exports data in JSON and
Prometheus formats.

### Design Goals

1. **Thread-safe**: All counter increments use atomic operations
2. **Minimal overhead**: < 0.1ms per metric recording
3. **Zero external dependencies**: Core functionality uses stdlib only
4. **Graceful degradation**: Metric failures do not impact tool execution

---

## 2. Data Structures

### 2.1 Constants and Configuration

```
CONSTANTS:
    # Histogram bucket boundaries in seconds
    # Covers range from 10ms to 10s for typical API latencies
    LATENCY_BUCKETS_SECONDS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    # Convert to milliseconds for internal storage
    LATENCY_BUCKETS_MS = (10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)

    # Error categories for classification
    ERROR_CATEGORIES = {
        "http_4xx": range(400, 500),
        "http_5xx": range(500, 600),
        "timeout": ["TimeoutException", "TimeoutError"],
        "connection": ["ConnectError", "ConnectionError"],
        "validation": ["ValueError", "ValidationError"],
        "unknown": []  # Catch-all
    }

    # Metric name prefix (configurable)
    DEFAULT_METRICS_PREFIX = "highlight"
```

### 2.2 ToolMetrics Dataclass

```
DATACLASS: ToolMetrics
PURPOSE: Store metrics for a single MCP tool

FIELDS:
    tool_name: string
        # The tool identifier (e.g., "highlight_get_company")

    calls_total: integer = 0
        # Total number of invocations (success + error)

    calls_success: integer = 0
        # Number of successful completions

    calls_error: integer = 0
        # Number of failed invocations

    latency_sum_ms: float = 0.0
        # Sum of all latencies in milliseconds (for average calculation)

    latency_buckets: dict[float, integer]
        # Histogram buckets: bucket_upper_bound -> count
        # Initialized with all bucket boundaries set to 0
        # Example: {10: 0, 25: 0, 50: 0, 100: 0, 250: 0, 500: 0, 1000: 0, 2500: 0, 5000: 0, 10000: 0, +Inf: 0}

    latency_values: list[float]
        # Raw latency values for percentile calculation
        # Bounded to prevent memory growth (max 10000 samples, sliding window)

    errors_by_type: dict[string, integer]
        # Error counts by category: "http_4xx" -> count

    last_call_timestamp: float | None = None
        # Unix timestamp of most recent call

CONSTRUCTOR:
    def __init__(self, tool_name: string):
        self.tool_name = tool_name
        self.calls_total = 0
        self.calls_success = 0
        self.calls_error = 0
        self.latency_sum_ms = 0.0
        self.latency_buckets = {}
        FOR EACH bucket IN LATENCY_BUCKETS_MS:
            self.latency_buckets[bucket] = 0
        self.latency_buckets[float("+inf")] = 0  # Infinity bucket
        self.latency_values = []
        self.errors_by_type = {}
        self.last_call_timestamp = None
```

### 2.3 HttpMetrics Dataclass

```
DATACLASS: HttpMetrics
PURPOSE: Store metrics for HTTP client requests to CAST Highlight API

FIELDS:
    requests_total: integer = 0
        # Total HTTP requests made

    requests_by_status: dict[integer, integer]
        # Status code counts: 200 -> count, 404 -> count, etc.

    requests_by_method: dict[string, integer]
        # Method counts: "GET" -> count, "POST" -> count

    latency_sum_ms: float = 0.0
        # Sum of HTTP request latencies

    latency_buckets: dict[float, integer]
        # Same structure as ToolMetrics

    latency_values: list[float]
        # Raw values for percentile calculation (bounded)

    errors_total: integer = 0
        # Total HTTP errors (4xx + 5xx + connection failures)

CONSTRUCTOR:
    def __init__(self):
        self.requests_total = 0
        self.requests_by_status = {}
        self.requests_by_method = {}
        self.latency_sum_ms = 0.0
        self.latency_buckets = {}
        FOR EACH bucket IN LATENCY_BUCKETS_MS:
            self.latency_buckets[bucket] = 0
        self.latency_buckets[float("+inf")] = 0
        self.latency_values = []
        self.errors_total = 0
```

### 2.4 ObservabilityState Dataclass

```
DATACLASS: ObservabilityState
PURPOSE: Global container for all observability metrics

FIELDS:
    start_time: float
        # Unix timestamp when metrics collection started

    tools: dict[string, ToolMetrics]
        # Tool name -> ToolMetrics mapping

    http: HttpMetrics
        # HTTP client metrics

    reset_count: integer = 0
        # Number of times metrics have been reset

    last_reset_time: float | None = None
        # Timestamp of last reset

CONSTRUCTOR:
    def __init__(self):
        self.start_time = time.time()
        self.tools = {}
        self.http = HttpMetrics()
        self.reset_count = 0
        self.last_reset_time = None
```

---

## 3. MetricsCollector Class

### 3.1 Class Definition and Initialization

```
CLASS: MetricsCollector
PURPOSE: Thread-safe metrics collection and export

ATTRIBUTES:
    _state: ObservabilityState
        # The metrics state container

    _lock: threading.Lock
        # Lock for thread-safe counter operations

    _enabled: boolean
        # Whether metrics collection is enabled

    _prefix: string
        # Metric name prefix for export

    _max_latency_samples: integer = 10000
        # Maximum latency samples to retain per metric

ALGORITHM: __init__
INPUT: enabled (boolean, default True), prefix (string, default "highlight")
OUTPUT: Initialized MetricsCollector instance

BEGIN
    self._state = ObservabilityState()
    self._lock = threading.Lock()
    self._enabled = enabled
    self._prefix = prefix
    self._max_latency_samples = 10000
END
```

### 3.2 Tool Call Recording

```
ALGORITHM: record_tool_call
PURPOSE: Record metrics for a completed tool invocation
INPUT:
    tool_name: string        # Name of the tool (e.g., "highlight_get_company")
    duration_ms: float       # Call duration in milliseconds
    success: boolean         # Whether the call succeeded
    error_type: string|None  # Error category if failed (optional)
OUTPUT: None (metrics updated in place)

PRECONDITIONS:
    - duration_ms >= 0
    - tool_name is non-empty string

BEGIN
    # Early return if metrics disabled
    IF NOT self._enabled THEN
        RETURN
    END IF

    # Wrap in try-catch for graceful degradation
    TRY:
        current_time = time.time()

        # Thread-safe metric update
        WITH self._lock:
            # Get or create tool metrics
            IF tool_name NOT IN self._state.tools THEN
                self._state.tools[tool_name] = ToolMetrics(tool_name)
            END IF

            metrics = self._state.tools[tool_name]

            # Increment counters (atomic within lock)
            metrics.calls_total = metrics.calls_total + 1

            IF success THEN
                metrics.calls_success = metrics.calls_success + 1
            ELSE
                metrics.calls_error = metrics.calls_error + 1

                # Classify and record error type
                error_category = self._classify_error(error_type)
                IF error_category NOT IN metrics.errors_by_type THEN
                    metrics.errors_by_type[error_category] = 0
                END IF
                metrics.errors_by_type[error_category] = metrics.errors_by_type[error_category] + 1
            END IF

            # Record latency
            metrics.latency_sum_ms = metrics.latency_sum_ms + duration_ms
            self._update_histogram_bucket(metrics.latency_buckets, duration_ms)
            self._append_latency_sample(metrics.latency_values, duration_ms)

            # Update timestamp
            metrics.last_call_timestamp = current_time

    CATCH Exception as e:
        # Log to stderr but don't raise - graceful degradation
        sys.stderr.write(f"Metrics recording error: {e}\n")
    END TRY
END
```

### 3.3 HTTP Request Recording

```
ALGORITHM: record_http_request
PURPOSE: Record metrics for an HTTP request to CAST Highlight API
INPUT:
    method: string           # HTTP method (GET, POST, etc.)
    status_code: integer     # Response status code (200, 404, 500, etc.)
    duration_ms: float       # Request duration in milliseconds
OUTPUT: None (metrics updated in place)

PRECONDITIONS:
    - method is valid HTTP method
    - status_code is valid HTTP status (100-599)
    - duration_ms >= 0

BEGIN
    IF NOT self._enabled THEN
        RETURN
    END IF

    TRY:
        WITH self._lock:
            http = self._state.http

            # Increment total counter
            http.requests_total = http.requests_total + 1

            # Increment status code counter
            IF status_code NOT IN http.requests_by_status THEN
                http.requests_by_status[status_code] = 0
            END IF
            http.requests_by_status[status_code] = http.requests_by_status[status_code] + 1

            # Increment method counter
            method_upper = method.upper()
            IF method_upper NOT IN http.requests_by_method THEN
                http.requests_by_method[method_upper] = 0
            END IF
            http.requests_by_method[method_upper] = http.requests_by_method[method_upper] + 1

            # Track errors (4xx, 5xx)
            IF status_code >= 400 THEN
                http.errors_total = http.errors_total + 1
            END IF

            # Record latency
            http.latency_sum_ms = http.latency_sum_ms + duration_ms
            self._update_histogram_bucket(http.latency_buckets, duration_ms)
            self._append_latency_sample(http.latency_values, duration_ms)

    CATCH Exception as e:
        sys.stderr.write(f"HTTP metrics recording error: {e}\n")
    END TRY
END
```

### 3.4 Histogram Bucket Update

```
ALGORITHM: _update_histogram_bucket
PURPOSE: Increment the appropriate histogram bucket for a latency value
INPUT:
    buckets: dict[float, integer]  # Bucket boundaries -> counts
    value_ms: float                # Latency value in milliseconds
OUTPUT: None (buckets updated in place)

EXPLANATION:
    Histogram buckets are cumulative - each bucket counts all observations
    less than or equal to the bucket boundary. This matches Prometheus
    histogram semantics.

BEGIN
    # Iterate through sorted bucket boundaries
    FOR EACH boundary IN sorted(buckets.keys()):
        # All buckets >= value get incremented (cumulative)
        IF value_ms <= boundary THEN
            buckets[boundary] = buckets[boundary] + 1
        END IF
    END FOR

    # Note: +Inf bucket always gets incremented (counts all observations)
    # This is handled by the loop since +Inf > all values
END

EXAMPLE:
    # Value: 75ms
    # Buckets: {10: 0, 25: 0, 50: 0, 100: 0, 250: 0, 500: 0, +Inf: 0}
    # After: {10: 0, 25: 0, 50: 0, 100: 1, 250: 1, 500: 1, +Inf: 1}
    # (75ms <= 100, 250, 500, +Inf)
```

### 3.5 Latency Sample Management

```
ALGORITHM: _append_latency_sample
PURPOSE: Add latency sample with bounded memory (sliding window)
INPUT:
    samples: list[float]   # Existing samples list
    value_ms: float        # New latency value
OUTPUT: None (samples list updated in place)

BEGIN
    samples.append(value_ms)

    # Enforce maximum sample count (sliding window)
    IF len(samples) > self._max_latency_samples THEN
        # Remove oldest sample
        samples.pop(0)
    END IF
END

COMPLEXITY ANALYSIS:
    - Time: O(1) for append, O(n) for pop(0) but amortized across many calls
    - Space: O(max_latency_samples) bounded

    Alternative: Use collections.deque with maxlen for O(1) operations
```

### 3.6 Error Classification

```
ALGORITHM: _classify_error
PURPOSE: Classify an error into a standard category
INPUT:
    error_type: string | None    # Exception class name or error description
OUTPUT: string                   # Error category

BEGIN
    IF error_type IS None THEN
        RETURN "unknown"
    END IF

    error_type_lower = error_type.lower()

    # Check for HTTP status errors
    IF "404" IN error_type OR "not found" IN error_type_lower THEN
        RETURN "http_404"
    END IF
    IF "401" IN error_type OR "unauthorized" IN error_type_lower THEN
        RETURN "http_401"
    END IF
    IF "403" IN error_type OR "forbidden" IN error_type_lower THEN
        RETURN "http_403"
    END IF
    IF "500" IN error_type OR "internal server" IN error_type_lower THEN
        RETURN "http_500"
    END IF

    # Check for 4xx range
    FOR code IN range(400, 500):
        IF str(code) IN error_type THEN
            RETURN "http_4xx"
        END IF
    END FOR

    # Check for 5xx range
    FOR code IN range(500, 600):
        IF str(code) IN error_type THEN
            RETURN "http_5xx"
        END IF
    END FOR

    # Check for timeout errors
    IF "timeout" IN error_type_lower THEN
        RETURN "timeout"
    END IF

    # Check for connection errors
    IF "connect" IN error_type_lower OR "connection" IN error_type_lower THEN
        RETURN "connection"
    END IF

    # Check for validation errors
    IF "validation" IN error_type_lower OR "valueerror" IN error_type_lower THEN
        RETURN "validation"
    END IF

    RETURN "unknown"
END
```

---

## 4. Percentile Calculation

### 4.1 Core Percentile Algorithm

```
ALGORITHM: calculate_percentile
PURPOSE: Calculate a specific percentile from latency samples
INPUT:
    samples: list[float]   # List of latency values
    percentile: float      # Desired percentile (0-100, e.g., 50, 95, 99)
OUTPUT: float              # Percentile value, or 0.0 if no samples

PRECONDITIONS:
    - 0 <= percentile <= 100

BEGIN
    IF len(samples) == 0 THEN
        RETURN 0.0
    END IF

    # Sort samples for percentile calculation
    sorted_samples = sorted(samples)
    n = len(sorted_samples)

    # Calculate index using linear interpolation
    # percentile/100 gives the fractional position (0.0 to 1.0)
    # Multiply by (n-1) to get the index in 0-based array
    index = (percentile / 100.0) * (n - 1)

    # Get lower and upper indices
    lower_index = floor(index)
    upper_index = ceil(index)

    # If index is exact integer, return that value
    IF lower_index == upper_index THEN
        RETURN sorted_samples[lower_index]
    END IF

    # Linear interpolation between adjacent values
    fraction = index - lower_index
    lower_value = sorted_samples[lower_index]
    upper_value = sorted_samples[upper_index]

    RETURN lower_value + (fraction * (upper_value - lower_value))
END

EXAMPLE:
    # Samples: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    # P50 (median): index = 0.5 * 9 = 4.5
    #   lower_index = 4, upper_index = 5
    #   fraction = 0.5
    #   result = 50 + 0.5 * (60 - 50) = 55
    # P95: index = 0.95 * 9 = 8.55
    #   lower_index = 8, upper_index = 9
    #   fraction = 0.55
    #   result = 90 + 0.55 * (100 - 90) = 95.5
```

### 4.2 Batch Percentile Calculation

```
ALGORITHM: calculate_percentiles
PURPOSE: Calculate multiple percentiles efficiently (single sort)
INPUT:
    samples: list[float]           # List of latency values
    percentiles: list[float]       # List of percentiles to calculate
OUTPUT: dict[float, float]         # Percentile -> value mapping

BEGIN
    IF len(samples) == 0 THEN
        result = {}
        FOR EACH p IN percentiles:
            result[p] = 0.0
        END FOR
        RETURN result
    END IF

    # Single sort for all percentiles
    sorted_samples = sorted(samples)
    n = len(sorted_samples)

    result = {}
    FOR EACH percentile IN percentiles:
        index = (percentile / 100.0) * (n - 1)
        lower_index = floor(index)
        upper_index = min(ceil(index), n - 1)  # Clamp to valid range

        IF lower_index == upper_index THEN
            result[percentile] = sorted_samples[lower_index]
        ELSE
            fraction = index - lower_index
            result[percentile] = (
                sorted_samples[lower_index] +
                fraction * (sorted_samples[upper_index] - sorted_samples[lower_index])
            )
        END IF
    END FOR

    RETURN result
END

COMPLEXITY:
    Time: O(n log n) for sort + O(k) for k percentiles = O(n log n)
    Space: O(n) for sorted copy
```

### 4.3 Percentile Helper Method

```
ALGORITHM: _get_latency_percentiles
PURPOSE: Get standard percentiles (p50, p90, p95, p99) for a latency list
INPUT:
    latency_values: list[float]    # Raw latency samples
OUTPUT: dict[string, float]        # Percentile name -> value

BEGIN
    percentiles = calculate_percentiles(
        latency_values,
        [50, 90, 95, 99]
    )

    RETURN {
        "p50_ms": round(percentiles[50], 2),
        "p90_ms": round(percentiles[90], 2),
        "p95_ms": round(percentiles[95], 2),
        "p99_ms": round(percentiles[99], 2)
    }
END
```

---

## 5. Export Formats

### 5.1 JSON Export

```
ALGORITHM: export_json
PURPOSE: Export all metrics as a JSON string
INPUT: None (uses internal state)
OUTPUT: string (JSON-formatted metrics)

BEGIN
    WITH self._lock:
        current_time = time.time()
        uptime_seconds = current_time - self._state.start_time

        # Build tools section
        tools_data = {}
        FOR EACH tool_name, metrics IN self._state.tools.items():
            percentiles = self._get_latency_percentiles(metrics.latency_values)

            # Calculate average latency
            avg_latency = 0.0
            IF metrics.calls_total > 0 THEN
                avg_latency = metrics.latency_sum_ms / metrics.calls_total
            END IF

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
                "last_call_timestamp": metrics.last_call_timestamp
            }
        END FOR

        # Build HTTP section
        http = self._state.http
        http_percentiles = self._get_latency_percentiles(http.latency_values)

        http_avg_latency = 0.0
        IF http.requests_total > 0 THEN
            http_avg_latency = http.latency_sum_ms / http.requests_total
        END IF

        http_data = {
            "requests_total": http.requests_total,
            "requests_by_status": dict(http.requests_by_status),
            "requests_by_method": dict(http.requests_by_method),
            "errors_total": http.errors_total,
            "latency_avg_ms": round(http_avg_latency, 2),
            "latency_p50_ms": http_percentiles["p50_ms"],
            "latency_p90_ms": http_percentiles["p90_ms"],
            "latency_p95_ms": http_percentiles["p95_ms"],
            "latency_p99_ms": http_percentiles["p99_ms"]
        }

        # Build complete export structure
        export_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": round(uptime_seconds, 2),
            "reset_count": self._state.reset_count,
            "last_reset_time": self._state.last_reset_time,
            "tools": tools_data,
            "http": http_data
        }

    RETURN json.dumps(export_data, indent=2)
END

OUTPUT EXAMPLE:
{
  "timestamp": "2026-01-29T12:34:56.789Z",
  "uptime_seconds": 3600.00,
  "reset_count": 0,
  "last_reset_time": null,
  "tools": {
    "highlight_get_company": {
      "calls_total": 150,
      "calls_success": 145,
      "calls_error": 5,
      "latency_avg_ms": 120.5,
      "latency_p50_ms": 110.2,
      "latency_p90_ms": 280.5,
      "latency_p95_ms": 450.2,
      "latency_p99_ms": 892.1,
      "errors_by_type": {"http_404": 3, "timeout": 2},
      "last_call_timestamp": 1738154096.789
    }
  },
  "http": {
    "requests_total": 200,
    "requests_by_status": {"200": 180, "404": 15, "500": 5},
    "requests_by_method": {"GET": 200},
    "errors_total": 20,
    "latency_avg_ms": 95.2,
    "latency_p50_ms": 85.0,
    "latency_p90_ms": 220.0,
    "latency_p95_ms": 320.4,
    "latency_p99_ms": 780.1
  }
}
```

### 5.2 Prometheus Export

```
ALGORITHM: export_prometheus
PURPOSE: Export metrics in Prometheus text exposition format
INPUT: None (uses internal state)
OUTPUT: string (Prometheus-formatted metrics)

BEGIN
    lines = []
    prefix = self._prefix

    WITH self._lock:
        # =====================================================
        # Tool Call Metrics
        # =====================================================

        # Tool calls total (counter)
        lines.append(f"# HELP {prefix}_tool_calls_total Total number of tool calls")
        lines.append(f"# TYPE {prefix}_tool_calls_total counter")

        FOR EACH tool_name, metrics IN self._state.tools.items():
            lines.append(
                f'{prefix}_tool_calls_total{{tool_name="{tool_name}",status="success"}} {metrics.calls_success}'
            )
            lines.append(
                f'{prefix}_tool_calls_total{{tool_name="{tool_name}",status="error"}} {metrics.calls_error}'
            )
        END FOR
        lines.append("")

        # Tool duration histogram
        lines.append(f"# HELP {prefix}_tool_duration_seconds Tool call duration in seconds")
        lines.append(f"# TYPE {prefix}_tool_duration_seconds histogram")

        FOR EACH tool_name, metrics IN self._state.tools.items():
            # Histogram buckets (convert ms to seconds for Prometheus convention)
            FOR EACH bucket_ms, count IN sorted(metrics.latency_buckets.items()):
                IF bucket_ms == float("+inf") THEN
                    le = "+Inf"
                ELSE
                    le = str(bucket_ms / 1000.0)  # Convert to seconds
                END IF
                lines.append(
                    f'{prefix}_tool_duration_seconds_bucket{{tool_name="{tool_name}",le="{le}"}} {count}'
                )
            END FOR

            # Sum and count
            sum_seconds = metrics.latency_sum_ms / 1000.0
            lines.append(
                f'{prefix}_tool_duration_seconds_sum{{tool_name="{tool_name}"}} {sum_seconds}'
            )
            lines.append(
                f'{prefix}_tool_duration_seconds_count{{tool_name="{tool_name}"}} {metrics.calls_total}'
            )
        END FOR
        lines.append("")

        # Tool errors by type (counter)
        lines.append(f"# HELP {prefix}_errors_total Total errors by type")
        lines.append(f"# TYPE {prefix}_errors_total counter")

        FOR EACH tool_name, metrics IN self._state.tools.items():
            FOR EACH error_type, count IN metrics.errors_by_type.items():
                lines.append(
                    f'{prefix}_errors_total{{tool_name="{tool_name}",error_type="{error_type}"}} {count}'
                )
            END FOR
        END FOR
        lines.append("")

        # =====================================================
        # HTTP Request Metrics
        # =====================================================

        http = self._state.http

        # HTTP requests total (counter)
        lines.append(f"# HELP {prefix}_http_requests_total Total HTTP requests to CAST API")
        lines.append(f"# TYPE {prefix}_http_requests_total counter")

        FOR EACH status_code, count IN sorted(http.requests_by_status.items()):
            # Determine method (default to GET since that's primary usage)
            lines.append(
                f'{prefix}_http_requests_total{{method="GET",status_code="{status_code}"}} {count}'
            )
        END FOR
        lines.append("")

        # HTTP duration histogram
        lines.append(f"# HELP {prefix}_http_duration_seconds HTTP request duration in seconds")
        lines.append(f"# TYPE {prefix}_http_duration_seconds histogram")

        FOR EACH bucket_ms, count IN sorted(http.latency_buckets.items()):
            IF bucket_ms == float("+inf") THEN
                le = "+Inf"
            ELSE
                le = str(bucket_ms / 1000.0)
            END IF
            lines.append(
                f'{prefix}_http_duration_seconds_bucket{{method="GET",le="{le}"}} {count}'
            )
        END FOR

        sum_seconds = http.latency_sum_ms / 1000.0
        lines.append(f'{prefix}_http_duration_seconds_sum{{method="GET"}} {sum_seconds}')
        lines.append(f'{prefix}_http_duration_seconds_count{{method="GET"}} {http.requests_total}')
        lines.append("")

        # =====================================================
        # Uptime Metric
        # =====================================================

        uptime = time.time() - self._state.start_time
        lines.append(f"# HELP {prefix}_uptime_seconds Server uptime in seconds")
        lines.append(f"# TYPE {prefix}_uptime_seconds gauge")
        lines.append(f"{prefix}_uptime_seconds {uptime}")

    RETURN "\n".join(lines)
END

OUTPUT EXAMPLE:
# HELP highlight_tool_calls_total Total number of tool calls
# TYPE highlight_tool_calls_total counter
highlight_tool_calls_total{tool_name="highlight_get_company",status="success"} 145
highlight_tool_calls_total{tool_name="highlight_get_company",status="error"} 5

# HELP highlight_tool_duration_seconds Tool call duration in seconds
# TYPE highlight_tool_duration_seconds histogram
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="0.01"} 5
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="0.1"} 50
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="0.5"} 140
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="1.0"} 148
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="+Inf"} 150
highlight_tool_duration_seconds_sum{tool_name="highlight_get_company"} 25.5
highlight_tool_duration_seconds_count{tool_name="highlight_get_company"} 150
```

---

## 6. Metrics Reset

```
ALGORITHM: reset
PURPOSE: Reset metrics to initial state (all or specific tool)
INPUT:
    tool_name: string | None    # Specific tool to reset, or None for all
OUTPUT: None (metrics reset in place)

BEGIN
    WITH self._lock:
        current_time = time.time()
        self._state.reset_count = self._state.reset_count + 1
        self._state.last_reset_time = current_time

        IF tool_name IS None THEN
            # Reset all metrics
            self._state.tools = {}
            self._state.http = HttpMetrics()
            self._state.start_time = current_time
        ELSE
            # Reset specific tool only
            IF tool_name IN self._state.tools THEN
                self._state.tools[tool_name] = ToolMetrics(tool_name)
            END IF
        END IF

    # Log reset event (INFO level)
    IF tool_name IS None THEN
        log_info("Metrics reset: all metrics cleared")
    ELSE
        log_info(f"Metrics reset: tool '{tool_name}' cleared")
    END IF
END
```

---

## 7. State Access Methods

```
ALGORITHM: get_metrics
PURPOSE: Get current metrics state snapshot
INPUT: None
OUTPUT: ObservabilityState (copy of current state)

BEGIN
    WITH self._lock:
        # Return a deep copy to prevent external modification
        RETURN deepcopy(self._state)
    END WITH
END

ALGORITHM: get_tool_metrics
PURPOSE: Get metrics for a specific tool
INPUT: tool_name: string
OUTPUT: ToolMetrics | None

BEGIN
    WITH self._lock:
        IF tool_name IN self._state.tools THEN
            RETURN deepcopy(self._state.tools[tool_name])
        ELSE
            RETURN None
        END IF
    END WITH
END

ALGORITHM: get_http_metrics
PURPOSE: Get HTTP client metrics
INPUT: None
OUTPUT: HttpMetrics

BEGIN
    WITH self._lock:
        RETURN deepcopy(self._state.http)
    END WITH
END
```

---

## 8. Global Instance Management

```
MODULE-LEVEL STATE:
    _metrics_collector: MetricsCollector | None = None
    _collector_lock: threading.Lock = threading.Lock()

ALGORITHM: get_metrics_collector
PURPOSE: Get or create the global MetricsCollector singleton
INPUT: None
OUTPUT: MetricsCollector instance

BEGIN
    global _metrics_collector

    IF _metrics_collector IS NOT None THEN
        RETURN _metrics_collector
    END IF

    WITH _collector_lock:
        # Double-check locking pattern
        IF _metrics_collector IS None THEN
            # Load configuration
            config = load_observability_config()
            _metrics_collector = MetricsCollector(
                enabled=config.metrics_enabled,
                prefix=config.metrics_prefix
            )
        END IF
        RETURN _metrics_collector
    END WITH
END

ALGORITHM: reset_metrics_collector
PURPOSE: Reset the global metrics collector (for testing)
INPUT: None
OUTPUT: None

BEGIN
    global _metrics_collector

    WITH _collector_lock:
        IF _metrics_collector IS NOT None THEN
            _metrics_collector.reset()
        END IF
    END WITH
END
```

---

## 9. Integration Points

### 9.1 server.py Integration

```
MODIFIED MODULE: src/cast_highlight_mcp/server.py

IMPORTS TO ADD:
    import time
    import uuid
    from .metrics import get_metrics_collector

MODIFIED ALGORITHM: call_tool
PURPOSE: Instrument tool calls with metrics collection
INPUT: name (string), arguments (dict)
OUTPUT: list[TextContent]

BEGIN
    # Generate request ID for correlation
    request_id = str(uuid.uuid4())[:8]

    # Get metrics collector
    metrics = get_metrics_collector()

    # Record start time
    start_time = time.perf_counter()

    api = get_client()
    success = True
    error_type = None

    TRY:
        # ... existing tool routing logic ...
        IF name == "highlight_get_company" THEN
            result = await api.get_company(arguments.get("company_id"))
        ELIF name == "highlight_list_domains" THEN
            result = await api.list_domains(arguments.get("company_id"))
        # ... other tools ...
        ELSE
            success = False
            error_type = "unknown_tool"
            RETURN [TextContent(type="text", text=f"Unknown tool: {name}")]
        END IF

        RETURN [TextContent(type="text", text=json.dumps(result, indent=2))]

    CATCH Exception as e:
        success = False
        error_type = type(e).__name__
        RETURN [TextContent(type="text", text=f"Error: {str(e)}")]

    FINALLY:
        # Calculate duration
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000.0

        # Record metrics (always, even on error)
        metrics.record_tool_call(
            tool_name=name,
            duration_ms=duration_ms,
            success=success,
            error_type=error_type
        )
    END TRY
END
```

### 9.2 client.py Integration

```
MODIFIED MODULE: src/cast_highlight_mcp/client.py

IMPORTS TO ADD:
    import time
    from .metrics import get_metrics_collector

MODIFIED ALGORITHM: _request
PURPOSE: Instrument HTTP requests with metrics collection
INPUT: method (string), path (string), **kwargs
OUTPUT: Any (JSON response)

BEGIN
    metrics = get_metrics_collector()
    client = await self._get_client()
    url = f"{self.base_url}{path}"

    # Record start time
    start_time = time.perf_counter()
    status_code = 0

    TRY:
        response = await client.request(method, url, **kwargs)
        status_code = response.status_code
        response.raise_for_status()
        RETURN response.json()

    CATCH httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        RAISE

    CATCH httpx.TimeoutException as e:
        status_code = 0  # No response received
        RAISE

    CATCH httpx.ConnectError as e:
        status_code = 0  # No response received
        RAISE

    FINALLY:
        # Calculate duration
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000.0

        # Record HTTP metrics
        metrics.record_http_request(
            method=method,
            status_code=status_code,
            duration_ms=duration_ms
        )
    END TRY
END
```

---

## 10. Thread Safety Analysis

### 10.1 Lock Scope

```
THREAD SAFETY STRATEGY:

1. Single Lock Pattern:
   - All MetricsCollector operations use a single lock (self._lock)
   - This prevents deadlocks from multiple lock acquisition
   - Trade-off: Lower concurrency but simpler correctness

2. Critical Sections:
   - Counter increments: Must be atomic (within lock)
   - Histogram updates: Must be atomic (within lock)
   - Export operations: Must see consistent state (within lock)

3. Lock-Free Operations:
   - Enabled check (boolean read is atomic in Python)
   - Error classification (stateless pure function)

4. Lock Contention Mitigation:
   - Keep critical sections short
   - Do JSON serialization outside lock (with copied data)
   - Use perf_counter() outside lock for timing
```

### 10.2 Concurrent Access Patterns

```
PATTERN: Read-Mostly Workload

Most operations are counter increments (writes), but export operations
(reads) may occur concurrently. Using a single Lock (not RLock) ensures:

1. Writers block other writers (correct)
2. Writers block readers (correct)
3. Readers block writers (correct)
4. Readers block readers (conservative but safe)

For higher concurrency, consider:
- threading.RLock for reentrant operations
- concurrent.futures.ThreadPoolExecutor for async export
- Lock-free counters using atomic operations (Python lacks native support)

RECOMMENDATION:
For the expected workload (< 100 tool calls/second), single Lock is sufficient.
```

---

## 11. Complexity Analysis

```
OPERATION COMPLEXITY:

record_tool_call:
    Time: O(b) where b = number of histogram buckets (10)
    Space: O(1) amortized

record_http_request:
    Time: O(b) where b = number of histogram buckets (10)
    Space: O(1) amortized

calculate_percentile:
    Time: O(n log n) where n = number of samples
    Space: O(n) for sorted copy

export_json:
    Time: O(t * n log n) where t = tools, n = samples per tool
    Space: O(t * n) for output

export_prometheus:
    Time: O(t * b) where t = tools, b = buckets
    Space: O(t * b) for output

reset:
    Time: O(1)
    Space: O(1)

MEMORY BOUNDS:
    Per tool: ~80KB max (10000 samples * 8 bytes)
    Total with 12 tools: ~1MB max
    HTTP metrics: ~80KB max

    Total maximum memory: < 2MB
```

---

## 12. Testing Strategy

```
UNIT TESTS:

1. test_tool_metrics_initialization:
   - Verify all fields initialized correctly
   - Verify histogram buckets created

2. test_record_tool_call_success:
   - Verify counters increment
   - Verify latency recorded in correct bucket
   - Verify latency_values updated

3. test_record_tool_call_error:
   - Verify error counter increments
   - Verify error_type classified correctly

4. test_histogram_bucket_assignment:
   - Test boundary conditions (exact bucket boundary)
   - Test cumulative nature (+Inf always incremented)

5. test_percentile_calculation:
   - Test with known data set
   - Test edge cases (empty, single element, even/odd counts)

6. test_json_export_format:
   - Validate JSON schema
   - Verify all fields present

7. test_prometheus_export_format:
   - Validate Prometheus format
   - Verify metric naming conventions

8. test_thread_safety:
   - Concurrent increments from multiple threads
   - Verify final count matches expected

9. test_metrics_reset:
   - Verify counters reset to zero
   - Verify reset_count increments
   - Verify partial reset (single tool)

10. test_graceful_degradation:
    - Verify tool works when metrics disabled
    - Verify no exceptions escape from metrics code
```

---

## Appendix A: File Layout

```
src/cast_highlight_mcp/
    __init__.py
    server.py          # Modified: import metrics, instrument call_tool
    client.py          # Modified: import metrics, instrument _request
    config.py          # Modified: add ObservabilityConfig
    metrics.py         # NEW: MetricsCollector and data classes
```

## Appendix B: Import Dependencies

```
STANDARD LIBRARY ONLY (for core):
    - dataclasses (dataclass decorator)
    - threading (Lock for thread safety)
    - time (perf_counter for timing, time for timestamps)
    - json (JSON export)
    - datetime (ISO timestamp formatting)
    - math (floor, ceil for percentile calculation)
    - copy (deepcopy for state snapshots)
    - sys (stderr for error output)

OPTIONAL:
    - prometheus_client (if installed, use native histograms)
```
