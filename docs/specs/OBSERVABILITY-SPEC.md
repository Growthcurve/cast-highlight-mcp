# SPARC Specification: Unified Observability

> **Document Version**: 1.0.0
> **Status**: Draft
> **Related Issues**: #7 (Logging), #18 (Metrics/Telemetry)
> **Author**: SPARC Specification Agent
> **Date**: 2026-01-29

---

## 1. Introduction

### 1.1 Purpose

This specification defines the requirements for implementing unified observability in the `cast-highlight-mcp` server. The observability system encompasses structured logging throughout the codebase and call metrics/telemetry to track tool usage patterns.

### 1.2 Scope

This specification covers:
- Structured logging implementation across all modules
- Call metrics collection and exposure
- Configuration options for observability features
- Performance constraints and optimization

### 1.3 Definitions

| Term | Definition |
|------|------------|
| **Tool** | An MCP-exposed function that AI agents can invoke (e.g., `highlight_get_company`) |
| **Structured Logging** | Log entries formatted as JSON with consistent fields |
| **Telemetry** | Quantitative measurements of system behavior (counts, latencies, rates) |
| **Redaction** | The process of removing or masking sensitive data from logs |

### 1.4 Current State Analysis

The codebase currently has:
- **Minimal logging**: Only `client.py` imports `logging` and uses it in `list_domains()` for error cases
- **No metrics collection**: No tracking of tool invocations, latencies, or error rates
- **No configuration**: No environment variables for logging/metrics settings

**Files requiring modification**:
- `/src/cast_highlight_mcp/server.py` - MCP server with 12 tools (no logging)
- `/src/cast_highlight_mcp/client.py` - HTTP client (partial logging)
- `/src/cast_highlight_mcp/config.py` - Configuration (no observability config)

---

## 2. Functional Requirements

### 2.1 Structured Logging

#### FR-LOG-001: Log Format

**Description**: All log entries SHALL be structured as JSON for machine parsing.

**Log Entry Schema**:
```json
{
  "timestamp": "2026-01-29T12:34:56.789Z",
  "level": "INFO",
  "logger": "cast_highlight_mcp.server",
  "message": "Tool call completed",
  "context": {
    "tool_name": "highlight_get_company",
    "duration_ms": 145.23,
    "success": true,
    "request_id": "uuid-v4"
  }
}
```

**Acceptance Criteria**:
- [ ] All log entries are valid JSON when output format is set to JSON
- [ ] Log entries include timestamp, level, logger name, and message
- [ ] Context fields are included in a nested `context` object
- [ ] Human-readable format is available as an alternative

#### FR-LOG-002: Log Levels

**Description**: The system SHALL use standard Python log levels appropriately.

| Level | Usage |
|-------|-------|
| `DEBUG` | Detailed diagnostic information: request/response payloads, internal state |
| `INFO` | Normal operational events: tool calls, successful API requests |
| `WARNING` | Unexpected but recoverable situations: rate limiting, retries, auth errors |
| `ERROR` | Failures requiring attention: API errors, configuration issues |
| `CRITICAL` | System-level failures: client initialization failure, unrecoverable states |

**Acceptance Criteria**:
- [ ] `DEBUG` logs include full request/response details (redacted)
- [ ] `INFO` logs record every tool invocation start and completion
- [ ] `WARNING` logs capture rate limits, retries, and 4xx responses
- [ ] `ERROR` logs capture 5xx responses and exceptions
- [ ] Log level is configurable via environment variable

#### FR-LOG-003: Tool Call Logging

**Description**: Every MCP tool invocation SHALL be logged with consistent fields.

**Required Log Points**:

1. **Tool Call Start** (INFO):
   ```json
   {
     "message": "Tool call started",
     "context": {
       "tool_name": "highlight_get_application",
       "arguments": {"application_id": 12345},
       "request_id": "abc-123"
     }
   }
   ```

2. **Tool Call Success** (INFO):
   ```json
   {
     "message": "Tool call completed",
     "context": {
       "tool_name": "highlight_get_application",
       "duration_ms": 234.5,
       "success": true,
       "request_id": "abc-123",
       "response_size_bytes": 1024
     }
   }
   ```

3. **Tool Call Failure** (ERROR):
   ```json
   {
     "message": "Tool call failed",
     "context": {
       "tool_name": "highlight_get_application",
       "duration_ms": 1523.4,
       "success": false,
       "error_type": "httpx.HTTPStatusError",
       "error_message": "404 Not Found",
       "request_id": "abc-123"
     }
   }
   ```

**Acceptance Criteria**:
- [ ] All 12 tools log start, success, and failure events
- [ ] Duration is measured in milliseconds with sub-millisecond precision
- [ ] Request ID correlates related log entries
- [ ] Arguments are logged at DEBUG level only

#### FR-LOG-004: HTTP Client Logging

**Description**: HTTP requests to CAST Highlight API SHALL be logged.

**Required Log Points**:

1. **Request Start** (DEBUG):
   ```json
   {
     "message": "HTTP request started",
     "context": {
       "method": "GET",
       "url": "/companies/123",
       "request_id": "abc-123"
     }
   }
   ```

2. **Request Complete** (DEBUG for 2xx, WARNING for 4xx, ERROR for 5xx):
   ```json
   {
     "message": "HTTP request completed",
     "context": {
       "method": "GET",
       "url": "/companies/123",
       "status_code": 200,
       "duration_ms": 145.2,
       "request_id": "abc-123"
     }
   }
   ```

**Acceptance Criteria**:
- [ ] All HTTP requests are logged with method and URL path
- [ ] Response status codes are logged
- [ ] 4xx responses logged at WARNING, 5xx at ERROR
- [ ] Full URLs (with base) are NOT logged (may contain sensitive info)

#### FR-LOG-005: Sensitive Data Redaction

**Description**: Sensitive data SHALL be redacted from all log entries.

**Sensitive Fields to Redact**:
| Field | Redaction Strategy |
|-------|---------------------|
| `access_token` | Replace with `[REDACTED]` |
| `Authorization` header | Replace value with `Bearer [REDACTED]` |
| API keys in URLs | Replace with `[REDACTED]` |
| Company ID (optional) | Configurable: show or redact |

**Acceptance Criteria**:
- [ ] Access tokens never appear in logs at any level
- [ ] Authorization headers show `Bearer [REDACTED]`
- [ ] No full API URLs with tokens are logged
- [ ] Redaction cannot be bypassed by changing log level

#### FR-LOG-006: Server Lifecycle Logging

**Description**: Server startup and shutdown events SHALL be logged.

**Required Log Points**:
1. **Server Starting** (INFO): Configuration loaded, client initializing
2. **Server Ready** (INFO): MCP server accepting connections
3. **Server Shutdown** (INFO): Clean shutdown initiated
4. **Server Error** (CRITICAL): Unrecoverable startup failure

**Acceptance Criteria**:
- [ ] Server startup logs include version and configuration summary
- [ ] Configuration summary does NOT include sensitive values
- [ ] Shutdown logs include reason if available

---

### 2.2 Call Metrics/Telemetry

#### FR-MET-001: Metrics Collection

**Description**: The system SHALL collect metrics for all tool invocations.

**Metrics to Collect**:

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `highlight_tool_calls_total` | Counter | `tool_name`, `status` | Total tool invocations |
| `highlight_tool_duration_seconds` | Histogram | `tool_name` | Tool call duration |
| `highlight_http_requests_total` | Counter | `method`, `status_code` | HTTP requests made |
| `highlight_http_duration_seconds` | Histogram | `method`, `endpoint` | HTTP request duration |
| `highlight_errors_total` | Counter | `tool_name`, `error_type` | Error count by type |

**Acceptance Criteria**:
- [ ] All 12 tools increment call counter on invocation
- [ ] Duration histogram captures latency distribution
- [ ] Status label differentiates `success` vs `error`
- [ ] Metrics persist across tool calls within a session

#### FR-MET-002: Latency Tracking

**Description**: The system SHALL track latency percentiles for tool calls.

**Histogram Buckets** (seconds):
```python
LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
```

**Derived Metrics**:
- p50 (median) latency
- p90 latency
- p95 latency
- p99 latency

**Acceptance Criteria**:
- [ ] Histogram buckets cover range from 10ms to 10s
- [ ] Percentiles can be calculated from histogram
- [ ] Separate histograms for tool calls vs HTTP requests

#### FR-MET-003: Error Rate Tracking

**Description**: The system SHALL track error rates by tool and error type.

**Error Categories**:
| Category | Description |
|----------|-------------|
| `http_4xx` | Client errors (400-499) |
| `http_5xx` | Server errors (500-599) |
| `timeout` | Request timeout exceeded |
| `connection` | Network connection failure |
| `validation` | Input validation failure |
| `unknown` | Unclassified errors |

**Acceptance Criteria**:
- [ ] Errors are categorized by type
- [ ] Error rate can be calculated as errors/total
- [ ] Each tool has independent error tracking

#### FR-MET-004: Metrics Exposure

**Description**: Collected metrics SHALL be accessible for monitoring.

**Exposure Methods**:

1. **In-Memory Access** (Required):
   - Metrics available via Python API
   - Used for internal reporting

2. **Prometheus Format** (Optional):
   - Standard `/metrics` endpoint format
   - Requires `prometheus_client` dependency

3. **JSON Export** (Required):
   - Metrics exportable as JSON
   - Used for logging metrics summary

**JSON Export Schema**:
```json
{
  "timestamp": "2026-01-29T12:34:56.789Z",
  "uptime_seconds": 3600,
  "tools": {
    "highlight_get_company": {
      "calls_total": 150,
      "calls_success": 145,
      "calls_error": 5,
      "latency_p50_ms": 120,
      "latency_p95_ms": 450,
      "latency_p99_ms": 890
    }
  },
  "http": {
    "requests_total": 200,
    "requests_by_status": {"200": 180, "404": 15, "500": 5}
  }
}
```

**Acceptance Criteria**:
- [ ] Metrics accessible without external dependencies
- [ ] Prometheus format available when library installed
- [ ] JSON export includes all collected metrics
- [ ] Export does not block tool execution

#### FR-MET-005: Metrics Reset

**Description**: Metrics SHALL be resettable for testing and monitoring windows.

**Reset Behavior**:
- All counters reset to zero
- Histograms reset (clear all buckets)
- Reset timestamp recorded

**Acceptance Criteria**:
- [ ] Reset function available via API
- [ ] Reset logs an INFO event
- [ ] Partial reset (single tool) supported

---

### 2.3 Configuration

#### FR-CFG-001: Logging Configuration

**Description**: Logging behavior SHALL be configurable via environment variables.

**Environment Variables**:
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HIGHLIGHT_LOG_LEVEL` | string | `INFO` | Minimum log level |
| `HIGHLIGHT_LOG_FORMAT` | string | `json` | Output format: `json` or `text` |
| `HIGHLIGHT_LOG_FILE` | string | (none) | Optional file path for log output |
| `HIGHLIGHT_LOG_REDACT_IDS` | bool | `false` | Redact company/app IDs |

**Acceptance Criteria**:
- [ ] Log level configurable without code changes
- [ ] Invalid log level defaults to INFO with warning
- [ ] JSON and text formats produce equivalent information
- [ ] File logging appends, does not overwrite

#### FR-CFG-002: Metrics Configuration

**Description**: Metrics collection SHALL be configurable via environment variables.

**Environment Variables**:
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HIGHLIGHT_METRICS_ENABLED` | bool | `true` | Enable/disable metrics collection |
| `HIGHLIGHT_METRICS_PREFIX` | string | `highlight` | Metric name prefix |
| `HIGHLIGHT_METRICS_DETAILED` | bool | `false` | Include per-endpoint metrics |

**Acceptance Criteria**:
- [ ] Metrics can be completely disabled
- [ ] Disabling metrics removes collection overhead
- [ ] Metric prefix customizable for multi-instance deployments

---

## 3. Non-Functional Requirements

### NFR-001: Performance Overhead

**Description**: Observability features SHALL have minimal impact on response time.

**Constraints**:
| Operation | Maximum Overhead |
|-----------|------------------|
| Log entry creation | < 1ms |
| Metric increment | < 0.1ms |
| Total per-call overhead | < 5ms |

**Measurement**:
- Benchmark tool calls with and without observability
- Overhead = (with_observability - without_observability)

**Acceptance Criteria**:
- [ ] Average overhead < 2ms per tool call
- [ ] p99 overhead < 5ms per tool call
- [ ] No blocking I/O in hot path (async log writes)

### NFR-002: Dependency Constraints

**Description**: The implementation SHALL minimize new dependencies.

**Allowed Dependencies**:
| Dependency | Status | Purpose |
|------------|--------|---------|
| Python `logging` | stdlib | Core logging |
| Python `time` | stdlib | Duration measurement |
| Python `json` | stdlib | Structured formatting |
| Python `dataclasses` | stdlib | Metrics storage |
| `prometheus_client` | optional | Prometheus export |

**Acceptance Criteria**:
- [ ] Core functionality works with stdlib only
- [ ] Prometheus export gracefully unavailable if not installed
- [ ] No new required runtime dependencies

### NFR-003: Thread Safety

**Description**: Observability components SHALL be thread-safe.

**Constraints**:
- Metrics counters use atomic operations
- Log handlers are thread-safe
- No race conditions in concurrent tool calls

**Acceptance Criteria**:
- [ ] Concurrent tool calls do not corrupt metrics
- [ ] Log entries are not interleaved
- [ ] No deadlocks under concurrent load

### NFR-004: Memory Efficiency

**Description**: Observability features SHALL not cause memory leaks.

**Constraints**:
- Bounded metric storage (no unbounded growth)
- Log buffering with limits
- No retention of request/response bodies

**Acceptance Criteria**:
- [ ] Memory usage stable over 10,000 tool calls
- [ ] No retained references to large objects
- [ ] Histogram buckets have fixed memory cost

### NFR-005: Graceful Degradation

**Description**: Observability failures SHALL not impact tool functionality.

**Constraints**:
- Logging errors do not raise exceptions
- Metrics errors do not raise exceptions
- Tool calls succeed even if observability fails

**Acceptance Criteria**:
- [ ] Tool call succeeds if logging fails
- [ ] Tool call succeeds if metrics fail
- [ ] Observability errors logged to stderr

---

## 4. Data Model

### 4.1 Metrics Data Structure

```python
@dataclass
class ToolMetrics:
    """Metrics for a single tool."""
    tool_name: str
    calls_total: int = 0
    calls_success: int = 0
    calls_error: int = 0
    latency_sum_ms: float = 0.0
    latency_buckets: dict[float, int] = field(default_factory=dict)
    errors_by_type: dict[str, int] = field(default_factory=dict)
    last_call_timestamp: float | None = None

@dataclass
class HttpMetrics:
    """Metrics for HTTP client."""
    requests_total: int = 0
    requests_by_status: dict[int, int] = field(default_factory=dict)
    latency_sum_ms: float = 0.0
    latency_buckets: dict[float, int] = field(default_factory=dict)

@dataclass
class ObservabilityState:
    """Global observability state."""
    start_time: float
    tools: dict[str, ToolMetrics] = field(default_factory=dict)
    http: HttpMetrics = field(default_factory=HttpMetrics)
```

### 4.2 Log Context Schema

```python
@dataclass
class LogContext:
    """Structured context for log entries."""
    request_id: str
    tool_name: str | None = None
    duration_ms: float | None = None
    success: bool | None = None
    error_type: str | None = None
    error_message: str | None = None
    http_method: str | None = None
    http_path: str | None = None
    http_status: int | None = None
```

---

## 5. API Design

### 5.1 Logging API

```python
# New module: src/cast_highlight_mcp/observability.py

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for the module."""
    pass

def configure_logging(config: ObservabilityConfig) -> None:
    """Configure logging based on settings."""
    pass

class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    pass

@contextmanager
def log_context(request_id: str, **kwargs) -> Generator[LogContext, None, None]:
    """Context manager for correlated logging."""
    pass
```

### 5.2 Metrics API

```python
# New module: src/cast_highlight_mcp/metrics.py

class MetricsCollector:
    """Collects and exposes metrics."""

    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        error_type: str | None = None
    ) -> None:
        """Record a tool call metric."""
        pass

    def record_http_request(
        self,
        method: str,
        status_code: int,
        duration_ms: float
    ) -> None:
        """Record an HTTP request metric."""
        pass

    def get_metrics(self) -> ObservabilityState:
        """Get current metrics state."""
        pass

    def export_json(self) -> str:
        """Export metrics as JSON."""
        pass

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        pass

    def reset(self, tool_name: str | None = None) -> None:
        """Reset metrics (all or specific tool)."""
        pass

# Global instance
_metrics: MetricsCollector | None = None

def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    pass
```

### 5.3 Configuration Extension

```python
# Extension to src/cast_highlight_mcp/config.py

@dataclass
class ObservabilityConfig:
    """Observability configuration."""
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"
    log_file: str | None = None
    log_redact_ids: bool = False
    metrics_enabled: bool = True
    metrics_prefix: str = "highlight"
    metrics_detailed: bool = False

def load_observability_config() -> ObservabilityConfig:
    """Load observability configuration from environment."""
    pass
```

---

## 6. Use Cases

### UC-001: Tool Call with Full Observability

**Actor**: AI Agent
**Preconditions**: Server running, observability enabled

**Flow**:
1. Agent invokes `highlight_get_company` tool
2. Server generates request ID
3. Server logs tool call start (INFO)
4. Server increments tool call counter
5. Client logs HTTP request start (DEBUG)
6. Client makes API request
7. Client logs HTTP response (DEBUG)
8. Client records HTTP metrics
9. Server logs tool call completion (INFO)
10. Server records tool metrics with duration
11. Server returns result to agent

**Postconditions**:
- Tool call logged with duration
- Metrics updated
- Result returned to agent

### UC-002: Error Handling with Observability

**Actor**: AI Agent
**Preconditions**: Server running, API returns error

**Flow**:
1. Agent invokes `highlight_get_application` with invalid ID
2. Server generates request ID
3. Server logs tool call start (INFO)
4. Client logs HTTP request start (DEBUG)
5. Client receives 404 response
6. Client logs HTTP error (WARNING)
7. Client records HTTP error metrics
8. Server logs tool call failure (ERROR)
9. Server records tool error metrics
10. Server returns error to agent

**Postconditions**:
- Error logged with type and message
- Error metrics incremented
- Error returned to agent (tool still works)

### UC-003: Metrics Export

**Actor**: Operations Engineer
**Preconditions**: Server running with metrics

**Flow**:
1. Engineer queries metrics endpoint
2. Server collects current metrics state
3. Server formats as JSON/Prometheus
4. Server returns metrics export

**Postconditions**:
- Metrics returned in requested format
- No impact on tool operations

---

## 7. Acceptance Criteria Summary

### Logging Acceptance Criteria

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| AC-L01 | All 12 tools log start/completion | Code review + test |
| AC-L02 | Logs are valid JSON | JSON schema validation |
| AC-L03 | Sensitive data redacted | Security test |
| AC-L04 | Log level configurable | Environment variable test |
| AC-L05 | Duration measured in milliseconds | Unit test |
| AC-L06 | Request IDs correlate entries | Log analysis test |

### Metrics Acceptance Criteria

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| AC-M01 | Call count increments correctly | Unit test |
| AC-M02 | Latency histogram populated | Unit test |
| AC-M03 | Error rates tracked by type | Unit test |
| AC-M04 | JSON export valid | Schema validation |
| AC-M05 | Prometheus export valid | Format validation |
| AC-M06 | Metrics persist across calls | Integration test |

### Performance Acceptance Criteria

| ID | Criterion | Verification Method |
|----|-----------|---------------------|
| AC-P01 | Overhead < 5ms per call | Benchmark test |
| AC-P02 | No memory leaks | Load test + profiling |
| AC-P03 | Thread-safe operations | Concurrency test |
| AC-P04 | Graceful degradation | Fault injection test |

---

## 8. Out of Scope

The following items are explicitly **NOT** included in this specification:

1. **Distributed Tracing**: Integration with Jaeger, Zipkin, or OpenTelemetry spans
2. **External Metrics Storage**: Pushing metrics to external systems (InfluxDB, Datadog)
3. **Alerting**: Threshold-based alerts or notifications
4. **Log Aggregation**: Shipping logs to external systems (ELK, Splunk)
5. **Dashboard**: Grafana dashboards or visualization
6. **Request Sampling**: Probabilistic logging for high-volume scenarios
7. **Custom Metrics**: User-defined metrics via configuration
8. **Metrics Persistence**: Saving metrics across server restarts
9. **Authentication Metrics**: Tracking auth failures separately
10. **Rate Limit Tracking**: Tracking rate limit hits from CAST API

---

## 9. Implementation Notes

### 9.1 Suggested Module Structure

```
src/cast_highlight_mcp/
    __init__.py
    server.py          # Modified: add logging, metrics calls
    client.py          # Modified: add HTTP logging, metrics
    config.py          # Modified: add observability config
    observability/     # New package
        __init__.py
        logging.py     # Structured logging utilities
        metrics.py     # Metrics collection
        context.py     # Request context management
```

### 9.2 Migration Path

1. **Phase 1**: Add configuration options (non-breaking)
2. **Phase 2**: Add logging infrastructure (non-breaking)
3. **Phase 3**: Instrument server.py with logging
4. **Phase 4**: Instrument client.py with logging
5. **Phase 5**: Add metrics collection
6. **Phase 6**: Add metrics export endpoints

### 9.3 Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit tests | Logging formatters, metrics calculations |
| Integration tests | End-to-end tool calls with observability |
| Performance tests | Overhead benchmarks |
| Security tests | Redaction verification |

---

## 10. References

- [Issue #7: Add logging throughout the codebase](https://github.com/Growthcurve/cast-highlight-mcp/issues/7)
- [Issue #18: Add call metrics/telemetry](https://github.com/Growthcurve/cast-highlight-mcp/issues/18)
- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)

---

## Appendix A: Example Log Output

### JSON Format

```json
{"timestamp": "2026-01-29T12:34:56.789Z", "level": "INFO", "logger": "cast_highlight_mcp.server", "message": "Server starting", "context": {"version": "0.1.0", "base_url": "https://app.casthighlight.com/WS2"}}
{"timestamp": "2026-01-29T12:34:56.890Z", "level": "INFO", "logger": "cast_highlight_mcp.server", "message": "Server ready", "context": {"tools_count": 12}}
{"timestamp": "2026-01-29T12:34:57.123Z", "level": "INFO", "logger": "cast_highlight_mcp.server", "message": "Tool call started", "context": {"tool_name": "highlight_get_company", "request_id": "a1b2c3d4"}}
{"timestamp": "2026-01-29T12:34:57.234Z", "level": "DEBUG", "logger": "cast_highlight_mcp.client", "message": "HTTP request started", "context": {"method": "GET", "path": "/companies/123", "request_id": "a1b2c3d4"}}
{"timestamp": "2026-01-29T12:34:57.456Z", "level": "DEBUG", "logger": "cast_highlight_mcp.client", "message": "HTTP request completed", "context": {"method": "GET", "path": "/companies/123", "status_code": 200, "duration_ms": 222.0, "request_id": "a1b2c3d4"}}
{"timestamp": "2026-01-29T12:34:57.458Z", "level": "INFO", "logger": "cast_highlight_mcp.server", "message": "Tool call completed", "context": {"tool_name": "highlight_get_company", "duration_ms": 335.0, "success": true, "request_id": "a1b2c3d4"}}
```

### Text Format

```
2026-01-29 12:34:56.789 INFO  [cast_highlight_mcp.server] Server starting version=0.1.0
2026-01-29 12:34:56.890 INFO  [cast_highlight_mcp.server] Server ready tools_count=12
2026-01-29 12:34:57.123 INFO  [cast_highlight_mcp.server] Tool call started tool=highlight_get_company request_id=a1b2c3d4
2026-01-29 12:34:57.234 DEBUG [cast_highlight_mcp.client] HTTP request started method=GET path=/companies/123 request_id=a1b2c3d4
2026-01-29 12:34:57.456 DEBUG [cast_highlight_mcp.client] HTTP request completed method=GET path=/companies/123 status=200 duration_ms=222.0 request_id=a1b2c3d4
2026-01-29 12:34:57.458 INFO  [cast_highlight_mcp.server] Tool call completed tool=highlight_get_company duration_ms=335.0 success=true request_id=a1b2c3d4
```

---

## Appendix B: Example Metrics Output

### JSON Export

```json
{
  "timestamp": "2026-01-29T12:34:56.789Z",
  "uptime_seconds": 3600,
  "tools": {
    "highlight_get_company": {
      "calls_total": 150,
      "calls_success": 145,
      "calls_error": 5,
      "latency_p50_ms": 120.5,
      "latency_p95_ms": 450.2,
      "latency_p99_ms": 892.1,
      "errors_by_type": {
        "http_404": 3,
        "timeout": 2
      }
    },
    "highlight_list_domains": {
      "calls_total": 45,
      "calls_success": 44,
      "calls_error": 1,
      "latency_p50_ms": 890.3,
      "latency_p95_ms": 2100.5,
      "latency_p99_ms": 3500.0,
      "errors_by_type": {
        "http_500": 1
      }
    }
  },
  "http": {
    "requests_total": 520,
    "requests_by_status": {
      "200": 490,
      "404": 20,
      "500": 10
    },
    "latency_p50_ms": 95.2,
    "latency_p95_ms": 320.4,
    "latency_p99_ms": 780.1
  }
}
```

### Prometheus Format

```prometheus
# HELP highlight_tool_calls_total Total number of tool calls
# TYPE highlight_tool_calls_total counter
highlight_tool_calls_total{tool_name="highlight_get_company",status="success"} 145
highlight_tool_calls_total{tool_name="highlight_get_company",status="error"} 5
highlight_tool_calls_total{tool_name="highlight_list_domains",status="success"} 44
highlight_tool_calls_total{tool_name="highlight_list_domains",status="error"} 1

# HELP highlight_tool_duration_seconds Tool call duration in seconds
# TYPE highlight_tool_duration_seconds histogram
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="0.01"} 5
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="0.1"} 50
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="0.5"} 140
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="1.0"} 148
highlight_tool_duration_seconds_bucket{tool_name="highlight_get_company",le="+Inf"} 150
highlight_tool_duration_seconds_sum{tool_name="highlight_get_company"} 25.5
highlight_tool_duration_seconds_count{tool_name="highlight_get_company"} 150

# HELP highlight_http_requests_total Total HTTP requests to CAST API
# TYPE highlight_http_requests_total counter
highlight_http_requests_total{method="GET",status_code="200"} 490
highlight_http_requests_total{method="GET",status_code="404"} 20
highlight_http_requests_total{method="GET",status_code="500"} 10

# HELP highlight_errors_total Total errors by type
# TYPE highlight_errors_total counter
highlight_errors_total{tool_name="highlight_get_company",error_type="http_404"} 3
highlight_errors_total{tool_name="highlight_get_company",error_type="timeout"} 2
highlight_errors_total{tool_name="highlight_list_domains",error_type="http_500"} 1
```
