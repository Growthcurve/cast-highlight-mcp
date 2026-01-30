# SPARC Architecture: Unified Observability

> **Document Version**: 1.0.0
> **Status**: Draft
> **Related Specification**: [OBSERVABILITY-SPEC.md](../OBSERVABILITY-SPEC.md)
> **Author**: SPARC Architecture Agent
> **Date**: 2026-01-29

---

## 1. Executive Summary

This architecture document defines the technical design for implementing unified observability (structured logging and metrics) in the `cast-highlight-mcp` server. The design prioritizes:

- **Minimal Disruption**: Observability integrates without changing existing tool behavior
- **Graceful Degradation**: Observability failures never break tool execution
- **Zero New Dependencies**: Uses only Python stdlib (prometheus_client is optional)
- **Thread Safety**: All metrics operations are atomic and safe for concurrent access

---

## 2. Module Dependency Diagram

```
+-----------------------------------------------------------------------------------+
|                              CAST Highlight MCP Server                            |
+-----------------------------------------------------------------------------------+

                                    Entry Point
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                   server.py                                       |
|  - MCP Server instance                                                            |
|  - Tool definitions (TOOLS list)                                                  |
|  - call_tool() handler                                                            |
|  - main() entry point                                                             |
+-----------------------------------------------------------------------------------+
         |                    |                    |                    |
         | imports            | imports            | imports            | imports
         v                    v                    v                    v
+----------------+   +----------------+   +-------------------+   +----------------+
|   client.py    |   |   config.py    |   | observability/    |   |  __init__.py   |
|                |   |                |   |   __init__.py     |   |  (version)     |
| HighlightClient|   | Config         |   +-------------------+   +----------------+
| - HTTP methods |   | load_config()  |            |
| - API calls    |   | Observability  |            | exports
+----------------+   |   Config       |            v
         |           +----------------+   +-------------------+
         |                    ^           | observability/    |
         | uses               |           |   logging.py      |
         v                    |           +-------------------+
+----------------+            |           | - get_logger()    |
|    httpx       |            |           | - configure_      |
| (external dep) |            |           |     logging()     |
+----------------+            |           | - Structured      |
                              |           |   LogFormatter    |
                              |           | - log_context()   |
                              |           +-------------------+
                              |                    |
                              |                    | imports
                              |                    v
                              |           +-------------------+
                              |           | observability/    |
                              +-----------+   context.py      |
                                          +-------------------+
                                          | - RequestContext  |
                                          | - context_var     |
                                          | - generate_       |
                                          |     request_id()  |
                                          +-------------------+
                                                   ^
                                                   |
                                          +-------------------+
                                          | observability/    |
                                          |   metrics.py      |
                                          +-------------------+
                                          | - MetricsCollector|
                                          | - ToolMetrics     |
                                          | - HttpMetrics     |
                                          | - get_metrics()   |
                                          | - record_*()      |
                                          +-------------------+

                              Python stdlib only (no new deps)
                              --------------------------------
                              logging, time, json, dataclasses,
                              threading, contextlib, contextvars,
                              uuid, datetime
```

### Dependency Rules

1. **observability/** is a self-contained package with no external dependencies
2. **server.py** imports from observability/ but observability/ never imports from server.py
3. **client.py** imports from observability/ for HTTP-level logging/metrics
4. **config.py** defines ObservabilityConfig which observability/ modules use
5. Circular imports are prevented by keeping context.py as the base module

---

## 3. Data Flow Diagram: Tool Call with Observability

```
+-------------+
|  AI Agent   |
+------+------+
       |
       | 1. MCP tool call: highlight_get_company({company_id: 123})
       v
+-----------------------------------------------------------------------------------+
|                                 server.py::call_tool()                            |
+-----------------------------------------------------------------------------------+
       |
       | 2. Generate request_id (uuid4)
       | 3. Set RequestContext in context_var
       v
+-----------------------------------------------------------------------------------+
|  observability/context.py                                                         |
|  +------------------+                                                             |
|  | RequestContext   |  request_id="a1b2c3d4"                                      |
|  | tool_name        |  tool_name="highlight_get_company"                          |
|  | start_time       |  start_time=1706538897.123                                  |
|  +------------------+                                                             |
+-----------------------------------------------------------------------------------+
       |
       | 4. Log: "Tool call started" (INFO)
       v
+-----------------------------------------------------------------------------------+
|  observability/logging.py                                                         |
|  +------------------+                                                             |
|  | StructuredLog    |  {"timestamp": "...", "level": "INFO",                      |
|  | Formatter        |   "message": "Tool call started",                           |
|  +------------------+   "context": {"tool_name": "...", "request_id": "..."}}     |
+-----------------------------------------------------------------------------------+
       |
       | 5. Call client method: api.get_company(123)
       v
+-----------------------------------------------------------------------------------+
|                              client.py::get_company()                             |
+-----------------------------------------------------------------------------------+
       |
       | 6. Log: "HTTP request started" (DEBUG)
       | 7. Start HTTP timer
       v
+-----------------------------------------------------------------------------------+
|                              client.py::_request()                                |
+-----------------------------------------------------------------------------------+
       |
       | 8. httpx.AsyncClient.request(GET, /companies/123)
       v
+-----------------------------------------------------------------------------------+
|                           CAST Highlight API                                      |
+-----------------------------------------------------------------------------------+
       |
       | 9. HTTP Response (200 OK, JSON body)
       v
+-----------------------------------------------------------------------------------+
|                              client.py::_request()                                |
+-----------------------------------------------------------------------------------+
       |
       | 10. Calculate HTTP duration
       | 11. Log: "HTTP request completed" (DEBUG)
       | 12. Record HTTP metrics (status=200, duration=145ms)
       v
+-----------------------------------------------------------------------------------+
|  observability/metrics.py                                                         |
|  +-------------------+                                                            |
|  | MetricsCollector  |  http.requests_total++                                     |
|  |   .record_http_   |  http.requests_by_status[200]++                            |
|  |    request()      |  http.latency_buckets[0.25]++                              |
|  +-------------------+  (duration: 0.145s < 0.25s bucket)                         |
+-----------------------------------------------------------------------------------+
       |
       | 13. Return parsed JSON response
       v
+-----------------------------------------------------------------------------------+
|                              server.py::call_tool()                               |
+-----------------------------------------------------------------------------------+
       |
       | 14. Calculate tool duration
       | 15. Log: "Tool call completed" (INFO)
       | 16. Record tool metrics (success=true, duration=335ms)
       v
+-----------------------------------------------------------------------------------+
|  observability/metrics.py                                                         |
|  +-------------------+                                                            |
|  | MetricsCollector  |  tools["highlight_get_company"].calls_total++              |
|  |   .record_tool_   |  tools["highlight_get_company"].calls_success++            |
|  |    call()         |  tools["highlight_get_company"].latency_buckets[0.5]++     |
|  +-------------------+                                                            |
+-----------------------------------------------------------------------------------+
       |
       | 17. Clear RequestContext
       | 18. Return TextContent with JSON result
       v
+-------------+
|  AI Agent   |  <-- Receives tool response
+-------------+
```

### Error Flow Variant

When an error occurs (e.g., HTTP 404), the flow diverges at step 9:

```
       | 9. HTTP Response (404 Not Found)
       v
+-----------------------------------------------------------------------------------+
|                              client.py::_request()                                |
+-----------------------------------------------------------------------------------+
       |
       | 10. Calculate HTTP duration
       | 11. Log: "HTTP request completed" (WARNING for 4xx)
       | 12. Record HTTP metrics (status=404, duration=89ms)
       | 13. Raise httpx.HTTPStatusError
       v
+-----------------------------------------------------------------------------------+
|                              server.py::call_tool()                               |
+-----------------------------------------------------------------------------------+
       |
       | 14. Catch exception in try/except
       | 15. Classify error type: "http_404"
       | 16. Log: "Tool call failed" (ERROR)
       | 17. Record tool metrics (success=false, error_type="http_404")
       | 18. Clear RequestContext
       | 19. Return TextContent with error message
       v
+-------------+
|  AI Agent   |  <-- Receives error response (tool still works!)
+-------------+
```

---

## 4. Configuration Loading Sequence

```
+-----------------------------------------------------------------------------------+
|                             Application Startup                                   |
+-----------------------------------------------------------------------------------+

server.py::main()
       |
       v
+-----------------------------------------------------------------------------------+
| 1. asyncio.run(run())                                                             |
+-----------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------+
| 2. config = load_config()                                                         |
|    - Loads base Config (HIGHLIGHT_BASE_URL, ACCESS_TOKEN, COMPANY_ID)             |
+-----------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------+
| 3. obs_config = load_observability_config()                                       |
|    - Reads HIGHLIGHT_LOG_LEVEL (default: "INFO")                                  |
|    - Reads HIGHLIGHT_LOG_FORMAT (default: "json")                                 |
|    - Reads HIGHLIGHT_LOG_FILE (default: None)                                     |
|    - Reads HIGHLIGHT_LOG_REDACT_IDS (default: false)                              |
|    - Reads HIGHLIGHT_METRICS_ENABLED (default: true)                              |
|    - Reads HIGHLIGHT_METRICS_PREFIX (default: "highlight")                        |
|    - Reads HIGHLIGHT_METRICS_DETAILED (default: false)                            |
+-----------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------+
| 4. configure_logging(obs_config)                                                  |
|    - Validates log level (defaults to INFO if invalid)                            |
|    - Creates StructuredLogFormatter (JSON or text)                                |
|    - Configures root logger for cast_highlight_mcp namespace                      |
|    - Adds file handler if log_file specified                                      |
|    - Stores redaction settings                                                    |
+-----------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------+
| 5. Initialize MetricsCollector (if metrics_enabled)                               |
|    - Creates global _metrics instance                                             |
|    - Records start_time for uptime calculation                                    |
|    - Pre-initializes ToolMetrics for all 12 tools                                 |
+-----------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------+
| 6. Log: "Server starting" (INFO)                                                  |
|    - Includes version, base_url (redacted token)                                  |
|    - Includes observability config summary                                        |
+-----------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------+
| 7. _client = HighlightClient(config)                                              |
|    - HTTP client initialized lazily on first request                              |
+-----------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------+
| 8. Log: "Server ready" (INFO)                                                     |
|    - Includes tools_count=12                                                      |
+-----------------------------------------------------------------------------------+
       |
       v
+-----------------------------------------------------------------------------------+
| 9. server.run(read_stream, write_stream, ...)                                     |
|    - MCP server now accepting connections                                         |
+-----------------------------------------------------------------------------------+


Environment Variable Validation
-------------------------------

+-----------------------------------------------------------------------------------+
| HIGHLIGHT_LOG_LEVEL validation:                                                   |
|                                                                                   |
|   Input        | Result       | Action                                           |
|   -------------|--------------|--------------------------------------------------|
|   "DEBUG"      | DEBUG        | Use as-is                                        |
|   "INFO"       | INFO         | Use as-is (default)                              |
|   "WARNING"    | WARNING      | Use as-is                                        |
|   "ERROR"      | ERROR        | Use as-is                                        |
|   "CRITICAL"   | CRITICAL     | Use as-is                                        |
|   "warn"       | WARNING      | Normalize case                                   |
|   "invalid"    | INFO         | Log warning, use default                         |
|   ""           | INFO         | Use default                                      |
|   None         | INFO         | Use default                                      |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| Boolean environment variable parsing:                                             |
|                                                                                   |
|   True values:  "true", "1", "yes", "on" (case-insensitive)                       |
|   False values: Everything else (including empty string, None)                    |
+-----------------------------------------------------------------------------------+
```

---

## 5. Error Handling Strategy: Graceful Degradation

### Core Principle

**Tool execution MUST succeed even if observability fails.**

All observability operations are wrapped in try/except blocks that:
1. Catch any exception
2. Log to stderr (bypassing the potentially broken logging system)
3. Continue normal execution

### Error Handling Layers

```
+-----------------------------------------------------------------------------------+
|                          Layer 1: Configuration Errors                            |
+-----------------------------------------------------------------------------------+
| Location: config.py::load_observability_config()                                  |
| Strategy: Use safe defaults, log warning to stderr                                |
|                                                                                   |
| Example:                                                                          |
|   HIGHLIGHT_LOG_LEVEL="invalid"                                                   |
|   -> stderr: "WARNING: Invalid log level 'invalid', using INFO"                   |
|   -> Continue with log_level="INFO"                                               |
|                                                                                   |
| Example:                                                                          |
|   HIGHLIGHT_LOG_FILE="/nonexistent/path/log.txt"                                  |
|   -> stderr: "WARNING: Cannot write to log file, using stderr only"              |
|   -> Continue with file logging disabled                                          |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                          Layer 2: Logging Errors                                  |
+-----------------------------------------------------------------------------------+
| Location: observability/logging.py                                                |
| Strategy: Catch and suppress, write to stderr                                     |
|                                                                                   |
| def safe_log(logger, level, message, **context):                                  |
|     try:                                                                          |
|         logger.log(level, message, extra={"context": context})                    |
|     except Exception as e:                                                        |
|         # Last resort: write to stderr                                            |
|         print(f"LOGGING_ERROR: {e}", file=sys.stderr)                             |
|                                                                                   |
| All logging calls in server.py and client.py use safe_log()                       |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                          Layer 3: Metrics Errors                                  |
+-----------------------------------------------------------------------------------+
| Location: observability/metrics.py                                                |
| Strategy: Catch and suppress, no side effects                                     |
|                                                                                   |
| class MetricsCollector:                                                           |
|     def record_tool_call(self, ...):                                              |
|         try:                                                                      |
|             # Actual metrics recording                                            |
|             with self._lock:                                                      |
|                 self._tools[tool_name].calls_total += 1                           |
|                 ...                                                               |
|         except Exception as e:                                                    |
|             # Silently fail - metrics are optional                                |
|             safe_log_error("Metrics error", error=str(e))                         |
|                                                                                   |
| Metrics errors never propagate to caller                                          |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                          Layer 4: Context Errors                                  |
+-----------------------------------------------------------------------------------+
| Location: observability/context.py                                                |
| Strategy: Return fallback values                                                  |
|                                                                                   |
| def get_request_id() -> str:                                                      |
|     try:                                                                          |
|         return _context_var.get().request_id                                      |
|     except LookupError:                                                           |
|         # Context not set - generate ephemeral ID                                 |
|         return f"ephemeral-{uuid.uuid4().hex[:8]}"                                |
|                                                                                   |
| Missing context never causes tool failure                                         |
+-----------------------------------------------------------------------------------+
```

### Degradation Matrix

```
+----------------------+----------------------+----------------------------------+
| Component Fails      | Impact               | Mitigation                       |
+----------------------+----------------------+----------------------------------+
| Log formatter        | No JSON logs         | Fall back to text format         |
| File handler         | No file logs         | Continue with stderr only        |
| Metrics increment    | Inaccurate counts    | Silent failure, tool works       |
| Histogram bucket     | Missing latency data | Silent failure, tool works       |
| Request context      | No correlation       | Use ephemeral request ID         |
| Prometheus export    | No /metrics output   | Return error JSON, tool works    |
| JSON export          | No metrics summary   | Return empty JSON, tool works    |
+----------------------+----------------------+----------------------------------+
```

### Implementation Pattern

```python
# Pattern used throughout observability code

def observed_operation():
    """Every observability operation follows this pattern."""
    try:
        # Actual observability work
        return perform_observation()
    except Exception as e:
        # 1. Never re-raise
        # 2. Log to stderr (bypass potentially broken logging)
        # 3. Return safe default
        _emit_stderr_warning(f"Observability error: {e}")
        return None  # or appropriate default
```

---

## 6. Thread Safety Approach

### Concurrency Model

The MCP server uses `asyncio` for concurrency. Multiple tool calls can execute concurrently within a single event loop. Thread safety concerns arise from:

1. **Shared Metrics State**: Multiple coroutines updating the same counters
2. **Shared Logger State**: Multiple coroutines writing logs
3. **Request Context**: Per-request context must not leak between coroutines

### Thread Safety Mechanisms

```
+-----------------------------------------------------------------------------------+
|                          1. Metrics: threading.Lock                               |
+-----------------------------------------------------------------------------------+
| File: observability/metrics.py                                                    |
|                                                                                   |
| class MetricsCollector:                                                           |
|     def __init__(self):                                                           |
|         self._lock = threading.Lock()  # Protects all mutable state               |
|         self._tools: dict[str, ToolMetrics] = {}                                  |
|         self._http = HttpMetrics()                                                |
|                                                                                   |
|     def record_tool_call(self, tool_name: str, duration_ms: float, ...):          |
|         with self._lock:  # Atomic update                                         |
|             metrics = self._tools.setdefault(tool_name, ToolMetrics(tool_name))   |
|             metrics.calls_total += 1                                              |
|             metrics.latency_sum_ms += duration_ms                                 |
|             self._update_histogram(metrics.latency_buckets, duration_ms)          |
|                                                                                   |
| Why threading.Lock and not asyncio.Lock?                                          |
| - Metrics updates are fast (<0.1ms), no I/O involved                              |
| - threading.Lock is simpler and works in both sync and async contexts             |
| - Avoids async overhead for CPU-bound operations                                  |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                          2. Logging: Built-in Thread Safety                       |
+-----------------------------------------------------------------------------------+
| File: observability/logging.py                                                    |
|                                                                                   |
| Python's logging module is thread-safe by design:                                 |
| - Handler.emit() acquires a lock before writing                                   |
| - Multiple loggers can safely write to the same handler                           |
|                                                                                   |
| Our StructuredLogFormatter is stateless:                                          |
|                                                                                   |
| class StructuredLogFormatter(logging.Formatter):                                  |
|     def format(self, record: logging.LogRecord) -> str:                           |
|         # No instance state modified - pure function                              |
|         return json.dumps({                                                       |
|             "timestamp": self.formatTime(record),                                 |
|             "level": record.levelname,                                            |
|             "logger": record.name,                                                |
|             "message": record.getMessage(),                                       |
|             "context": getattr(record, "context", {}),                            |
|         })                                                                        |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                          3. Request Context: contextvars                          |
+-----------------------------------------------------------------------------------+
| File: observability/context.py                                                    |
|                                                                                   |
| from contextvars import ContextVar                                                |
|                                                                                   |
| @dataclass                                                                        |
| class RequestContext:                                                             |
|     request_id: str                                                               |
|     tool_name: str                                                                |
|     start_time: float                                                             |
|                                                                                   |
| _context_var: ContextVar[RequestContext] = ContextVar("request_context")          |
|                                                                                   |
| Why contextvars?                                                                  |
| - Designed for asyncio: each coroutine gets isolated context                      |
| - Automatically copied to child coroutines                                        |
| - No manual cleanup needed (context is scoped to coroutine lifetime)              |
|                                                                                   |
| @contextmanager                                                                   |
| def request_context(tool_name: str) -> Generator[RequestContext, None, None]:     |
|     ctx = RequestContext(                                                         |
|         request_id=str(uuid.uuid4()),                                             |
|         tool_name=tool_name,                                                      |
|         start_time=time.perf_counter(),                                           |
|     )                                                                             |
|     token = _context_var.set(ctx)                                                 |
|     try:                                                                          |
|         yield ctx                                                                 |
|     finally:                                                                      |
|         _context_var.reset(token)                                                 |
+-----------------------------------------------------------------------------------+
```

### Concurrency Safety Matrix

```
+----------------------+-------------------+------------------+---------------------+
| Component            | Shared State      | Protection       | Safe for asyncio?   |
+----------------------+-------------------+------------------+---------------------+
| MetricsCollector     | _tools, _http     | threading.Lock   | Yes                 |
| ToolMetrics          | counters, buckets | Parent lock      | Yes (via Collector) |
| HttpMetrics          | counters, buckets | Parent lock      | Yes (via Collector) |
| StructuredFormatter  | None (stateless)  | N/A              | Yes                 |
| RequestContext       | Per-coroutine     | contextvars      | Yes                 |
| Logger handlers      | Output stream     | Built-in lock    | Yes                 |
+----------------------+-------------------+------------------+---------------------+
```

---

## 7. File-by-File Change Summary

### Existing Files to Modify

```
+-----------------------------------------------------------------------------------+
| File: src/cast_highlight_mcp/config.py                                            |
+-----------------------------------------------------------------------------------+
| Changes:                                                                          |
|   1. Add ObservabilityConfig dataclass                                            |
|   2. Add load_observability_config() function                                     |
|   3. Add helper for parsing boolean env vars                                      |
|   4. Add helper for validating log levels                                         |
|                                                                                   |
| New Code (~50 lines):                                                             |
|   @dataclass                                                                      |
|   class ObservabilityConfig:                                                      |
|       log_level: str = "INFO"                                                     |
|       log_format: str = "json"                                                    |
|       log_file: str | None = None                                                 |
|       log_redact_ids: bool = False                                                |
|       metrics_enabled: bool = True                                                |
|       metrics_prefix: str = "highlight"                                           |
|       metrics_detailed: bool = False                                              |
|                                                                                   |
|   def load_observability_config() -> ObservabilityConfig: ...                     |
|   def _parse_bool(value: str | None) -> bool: ...                                 |
|   def _validate_log_level(level: str) -> str: ...                                 |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: src/cast_highlight_mcp/server.py                                            |
+-----------------------------------------------------------------------------------+
| Changes:                                                                          |
|   1. Import observability modules                                                 |
|   2. Initialize observability in main()                                           |
|   3. Wrap call_tool() with request context and logging                            |
|   4. Add metrics recording for tool calls                                         |
|   5. Add server lifecycle logging                                                 |
|                                                                                   |
| Modified: call_tool() function                                                    |
|                                                                                   |
| Before:                                                                           |
|   @server.call_tool()                                                             |
|   async def call_tool(name: str, arguments: dict) -> list[TextContent]:           |
|       api = get_client()                                                          |
|       try:                                                                        |
|           if name == "highlight_get_company":                                     |
|               result = await api.get_company(...)                                 |
|           ...                                                                     |
|       except Exception as e:                                                      |
|           return [TextContent(type="text", text=f"Error: {str(e)}")]              |
|                                                                                   |
| After:                                                                            |
|   @server.call_tool()                                                             |
|   async def call_tool(name: str, arguments: dict) -> list[TextContent]:           |
|       api = get_client()                                                          |
|       metrics = get_metrics()                                                     |
|                                                                                   |
|       with request_context(name) as ctx:                                          |
|           logger.info("Tool call started", tool_name=name, request_id=ctx.id)     |
|                                                                                   |
|           try:                                                                    |
|               if name == "highlight_get_company":                                 |
|                   result = await api.get_company(...)                             |
|               ...                                                                 |
|                                                                                   |
|               duration = ctx.elapsed_ms()                                         |
|               logger.info("Tool call completed", tool_name=name,                  |
|                          duration_ms=duration, success=True)                      |
|               metrics.record_tool_call(name, duration, success=True)              |
|               return [TextContent(...)]                                           |
|                                                                                   |
|           except Exception as e:                                                  |
|               duration = ctx.elapsed_ms()                                         |
|               error_type = classify_error(e)                                      |
|               logger.error("Tool call failed", tool_name=name,                    |
|                           duration_ms=duration, error_type=error_type)            |
|               metrics.record_tool_call(name, duration, success=False,             |
|                                       error_type=error_type)                      |
|               return [TextContent(type="text", text=f"Error: {str(e)}")]          |
|                                                                                   |
| Modified: main() function - add observability initialization                      |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: src/cast_highlight_mcp/client.py                                            |
+-----------------------------------------------------------------------------------+
| Changes:                                                                          |
|   1. Import observability modules                                                 |
|   2. Replace basic logger with structured logger                                  |
|   3. Add HTTP request/response logging in _request()                              |
|   4. Add HTTP metrics recording                                                   |
|   5. Use request context for correlation                                          |
|                                                                                   |
| Modified: _request() method                                                       |
|                                                                                   |
| Before:                                                                           |
|   async def _request(self, method: str, path: str, **kwargs) -> Any:              |
|       client = await self._get_client()                                           |
|       url = f"{self.base_url}{path}"                                              |
|       response = await client.request(method, url, **kwargs)                      |
|       response.raise_for_status()                                                 |
|       return response.json()                                                      |
|                                                                                   |
| After:                                                                            |
|   async def _request(self, method: str, path: str, **kwargs) -> Any:              |
|       client = await self._get_client()                                           |
|       url = f"{self.base_url}{path}"                                              |
|       request_id = get_request_id()                                               |
|       metrics = get_metrics()                                                     |
|                                                                                   |
|       logger.debug("HTTP request started", method=method, path=path,              |
|                   request_id=request_id)                                          |
|       start_time = time.perf_counter()                                            |
|                                                                                   |
|       try:                                                                        |
|           response = await client.request(method, url, **kwargs)                  |
|           duration_ms = (time.perf_counter() - start_time) * 1000                 |
|                                                                                   |
|           log_level = logging.DEBUG if response.status_code < 400 else            |
|                      (logging.WARNING if response.status_code < 500 else          |
|                       logging.ERROR)                                              |
|           logger.log(log_level, "HTTP request completed", method=method,          |
|                     path=path, status_code=response.status_code,                  |
|                     duration_ms=duration_ms, request_id=request_id)               |
|           metrics.record_http_request(method, response.status_code, duration_ms)  |
|                                                                                   |
|           response.raise_for_status()                                             |
|           return response.json()                                                  |
|       except Exception as e:                                                      |
|           duration_ms = (time.perf_counter() - start_time) * 1000                 |
|           logger.error("HTTP request failed", method=method, path=path,           |
|                       error=str(e), duration_ms=duration_ms,                      |
|                       request_id=request_id)                                      |
|           raise                                                                   |
|                                                                                   |
| Note: list_domains() already has some logging - standardize to new pattern        |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: src/cast_highlight_mcp/__init__.py                                          |
+-----------------------------------------------------------------------------------+
| Changes:                                                                          |
|   1. Export observability configuration                                           |
|   2. Export version for logging                                                   |
|                                                                                   |
| Additions:                                                                        |
|   from .observability import configure_logging, get_metrics                       |
+-----------------------------------------------------------------------------------+
```

### New Files to Create

```
+-----------------------------------------------------------------------------------+
| File: src/cast_highlight_mcp/observability/__init__.py                            |
+-----------------------------------------------------------------------------------+
| Purpose: Package initialization and public API exports                            |
| Size: ~30 lines                                                                   |
|                                                                                   |
| Contents:                                                                         |
|   """Observability package for structured logging and metrics."""                 |
|                                                                                   |
|   from .logging import (                                                          |
|       configure_logging,                                                          |
|       get_logger,                                                                 |
|       StructuredLogFormatter,                                                     |
|       TextLogFormatter,                                                           |
|   )                                                                               |
|   from .metrics import (                                                          |
|       MetricsCollector,                                                           |
|       get_metrics,                                                                |
|       ToolMetrics,                                                                |
|       HttpMetrics,                                                                |
|   )                                                                               |
|   from .context import (                                                          |
|       RequestContext,                                                             |
|       request_context,                                                            |
|       get_request_id,                                                             |
|   )                                                                               |
|                                                                                   |
|   __all__ = [                                                                     |
|       "configure_logging",                                                        |
|       "get_logger",                                                               |
|       "get_metrics",                                                              |
|       "get_request_id",                                                           |
|       "request_context",                                                          |
|       "MetricsCollector",                                                         |
|       "RequestContext",                                                           |
|       "StructuredLogFormatter",                                                   |
|       "TextLogFormatter",                                                         |
|       "ToolMetrics",                                                              |
|       "HttpMetrics",                                                              |
|   ]                                                                               |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: src/cast_highlight_mcp/observability/context.py                             |
+-----------------------------------------------------------------------------------+
| Purpose: Request context management using contextvars                             |
| Size: ~60 lines                                                                   |
|                                                                                   |
| Contents:                                                                         |
|   - RequestContext dataclass (request_id, tool_name, start_time)                  |
|   - _context_var: ContextVar for per-coroutine context                            |
|   - request_context(): context manager for setting/clearing context               |
|   - get_request_id(): safe getter with fallback                                   |
|   - get_context(): get full context or None                                       |
|                                                                                   |
| Key Implementation:                                                               |
|   @dataclass                                                                      |
|   class RequestContext:                                                           |
|       request_id: str                                                             |
|       tool_name: str                                                              |
|       start_time: float                                                           |
|                                                                                   |
|       def elapsed_ms(self) -> float:                                              |
|           return (time.perf_counter() - self.start_time) * 1000                   |
|                                                                                   |
|   _context_var: ContextVar[RequestContext] = ContextVar("request_context")        |
|                                                                                   |
|   @contextmanager                                                                 |
|   def request_context(tool_name: str) -> Generator[RequestContext, None, None]:   |
|       ctx = RequestContext(                                                       |
|           request_id=str(uuid.uuid4()),                                           |
|           tool_name=tool_name,                                                    |
|           start_time=time.perf_counter(),                                         |
|       )                                                                           |
|       token = _context_var.set(ctx)                                               |
|       try:                                                                        |
|           yield ctx                                                               |
|       finally:                                                                    |
|           _context_var.reset(token)                                               |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: src/cast_highlight_mcp/observability/logging.py                             |
+-----------------------------------------------------------------------------------+
| Purpose: Structured logging configuration and formatters                          |
| Size: ~150 lines                                                                  |
|                                                                                   |
| Contents:                                                                         |
|   - StructuredLogFormatter: JSON output format                                    |
|   - TextLogFormatter: Human-readable output format                                |
|   - configure_logging(): Set up logging based on config                           |
|   - get_logger(): Get a configured logger for a module                            |
|   - _redact_sensitive(): Remove tokens/secrets from log context                   |
|                                                                                   |
| Key Implementation:                                                               |
|   class StructuredLogFormatter(logging.Formatter):                                |
|       def __init__(self, redact_ids: bool = False):                               |
|           super().__init__()                                                      |
|           self.redact_ids = redact_ids                                            |
|                                                                                   |
|       def format(self, record: logging.LogRecord) -> str:                         |
|           context = getattr(record, "context", {})                                |
|           context = _redact_sensitive(context, self.redact_ids)                   |
|           return json.dumps({                                                     |
|               "timestamp": datetime.utcnow().isoformat() + "Z",                   |
|               "level": record.levelname,                                          |
|               "logger": record.name,                                              |
|               "message": record.getMessage(),                                     |
|               "context": context,                                                 |
|           })                                                                      |
|                                                                                   |
|   def configure_logging(config: ObservabilityConfig) -> None:                     |
|       root_logger = logging.getLogger("cast_highlight_mcp")                       |
|       root_logger.setLevel(getattr(logging, config.log_level))                    |
|                                                                                   |
|       formatter = (StructuredLogFormatter(config.log_redact_ids)                  |
|                   if config.log_format == "json"                                  |
|                   else TextLogFormatter(config.log_redact_ids))                   |
|                                                                                   |
|       handler = logging.StreamHandler()                                           |
|       handler.setFormatter(formatter)                                             |
|       root_logger.addHandler(handler)                                             |
|                                                                                   |
|       if config.log_file:                                                         |
|           try:                                                                    |
|               file_handler = logging.FileHandler(config.log_file)                 |
|               file_handler.setFormatter(formatter)                                |
|               root_logger.addHandler(file_handler)                                |
|           except (IOError, OSError) as e:                                         |
|               print(f"WARNING: Cannot write to log file: {e}", file=sys.stderr)   |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: src/cast_highlight_mcp/observability/metrics.py                             |
+-----------------------------------------------------------------------------------+
| Purpose: Metrics collection and export                                            |
| Size: ~250 lines                                                                  |
|                                                                                   |
| Contents:                                                                         |
|   - ToolMetrics dataclass                                                         |
|   - HttpMetrics dataclass                                                         |
|   - MetricsCollector class with thread-safe recording                             |
|   - get_metrics(): Get global metrics instance                                    |
|   - Histogram bucket logic                                                        |
|   - JSON and Prometheus export                                                    |
|                                                                                   |
| Key Implementation:                                                               |
|   LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)      |
|                                                                                   |
|   @dataclass                                                                      |
|   class ToolMetrics:                                                              |
|       tool_name: str                                                              |
|       calls_total: int = 0                                                        |
|       calls_success: int = 0                                                      |
|       calls_error: int = 0                                                        |
|       latency_sum_ms: float = 0.0                                                 |
|       latency_buckets: dict[float, int] = field(default_factory=dict)             |
|       errors_by_type: dict[str, int] = field(default_factory=dict)                |
|                                                                                   |
|   class MetricsCollector:                                                         |
|       def __init__(self, prefix: str = "highlight", enabled: bool = True):        |
|           self._prefix = prefix                                                   |
|           self._enabled = enabled                                                 |
|           self._lock = threading.Lock()                                           |
|           self._start_time = time.time()                                          |
|           self._tools: dict[str, ToolMetrics] = {}                                |
|           self._http = HttpMetrics()                                              |
|                                                                                   |
|       def record_tool_call(self, tool_name: str, duration_ms: float,              |
|                           success: bool, error_type: str | None = None):          |
|           if not self._enabled:                                                   |
|               return                                                              |
|           try:                                                                    |
|               with self._lock:                                                    |
|                   metrics = self._tools.setdefault(                               |
|                       tool_name, ToolMetrics(tool_name))                          |
|                   metrics.calls_total += 1                                        |
|                   if success:                                                     |
|                       metrics.calls_success += 1                                  |
|                   else:                                                           |
|                       metrics.calls_error += 1                                    |
|                       if error_type:                                              |
|                           metrics.errors_by_type[error_type] = \                  |
|                               metrics.errors_by_type.get(error_type, 0) + 1       |
|                   metrics.latency_sum_ms += duration_ms                           |
|                   self._update_histogram(metrics.latency_buckets,                 |
|                                         duration_ms / 1000)  # Convert to seconds |
|           except Exception:                                                       |
|               pass  # Graceful degradation                                        |
|                                                                                   |
|       def export_json(self) -> str:                                               |
|           with self._lock:                                                        |
|               return json.dumps(self._build_export_dict(), indent=2)              |
|                                                                                   |
|       def export_prometheus(self) -> str:                                         |
|           # Generates Prometheus text format                                      |
|           # No dependency on prometheus_client for basic export                   |
|           ...                                                                     |
|                                                                                   |
|   _metrics: MetricsCollector | None = None                                        |
|                                                                                   |
|   def get_metrics() -> MetricsCollector:                                          |
|       global _metrics                                                             |
|       if _metrics is None:                                                        |
|           _metrics = MetricsCollector()                                           |
|       return _metrics                                                             |
+-----------------------------------------------------------------------------------+
```

---

## 8. Testing Strategy

### Test File Structure

```
tests/
    __init__.py
    conftest.py                        # Existing + new fixtures
    unit/
        __init__.py
        test_config.py                 # Existing
        test_server.py                 # Existing
        test_client.py                 # Existing
        test_server_call_tool.py       # Existing
        test_client_http.py            # Existing
        observability/                 # NEW DIRECTORY
            __init__.py
            test_context.py            # NEW
            test_logging.py            # NEW
            test_metrics.py            # NEW
            test_config_observability.py  # NEW
    integration/                       # NEW DIRECTORY
        __init__.py
        test_observability_e2e.py      # NEW
    performance/                       # NEW DIRECTORY (optional)
        __init__.py
        test_observability_overhead.py # NEW
```

### Test Files Detail

```
+-----------------------------------------------------------------------------------+
| File: tests/unit/observability/test_context.py                                    |
+-----------------------------------------------------------------------------------+
| Purpose: Test request context management                                          |
| Coverage: context.py (100%)                                                       |
|                                                                                   |
| Test Cases:                                                                       |
|   test_request_context_creates_unique_id()                                        |
|     - Verify each context has a unique UUID                                       |
|                                                                                   |
|   test_request_context_stores_tool_name()                                         |
|     - Verify tool name is stored correctly                                        |
|                                                                                   |
|   test_request_context_elapsed_time()                                             |
|     - Verify elapsed_ms() returns increasing values                               |
|     - Use time.sleep(0.01) to verify timing                                       |
|                                                                                   |
|   test_request_context_cleanup()                                                  |
|     - Verify context is cleared after context manager exits                       |
|     - get_request_id() should return ephemeral ID after exit                      |
|                                                                                   |
|   test_get_request_id_without_context()                                           |
|     - Verify fallback to ephemeral ID when no context set                         |
|                                                                                   |
|   test_nested_contexts()                                                          |
|     - Verify nested contexts work correctly (inner overrides outer)               |
|                                                                                   |
|   test_concurrent_contexts()                                                      |
|     - Use asyncio.gather to run multiple coroutines                               |
|     - Verify each coroutine has isolated context                                  |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: tests/unit/observability/test_logging.py                                    |
+-----------------------------------------------------------------------------------+
| Purpose: Test logging formatters and configuration                                |
| Coverage: logging.py (100%)                                                       |
|                                                                                   |
| Test Cases:                                                                       |
|   test_structured_log_formatter_json_output()                                     |
|     - Verify output is valid JSON                                                 |
|     - Verify required fields: timestamp, level, logger, message                   |
|                                                                                   |
|   test_structured_log_formatter_context()                                         |
|     - Verify context dict is included in output                                   |
|                                                                                   |
|   test_structured_log_formatter_redaction()                                       |
|     - Verify access_token is replaced with [REDACTED]                             |
|     - Verify Authorization header shows "Bearer [REDACTED]"                       |
|                                                                                   |
|   test_structured_log_formatter_redact_ids()                                      |
|     - Verify company_id and app_id are redacted when configured                   |
|                                                                                   |
|   test_text_log_formatter_output()                                                |
|     - Verify human-readable format                                                |
|     - Verify key=value pairs in output                                            |
|                                                                                   |
|   test_configure_logging_json_format()                                            |
|     - Verify JSON formatter is used when format="json"                            |
|                                                                                   |
|   test_configure_logging_text_format()                                            |
|     - Verify text formatter is used when format="text"                            |
|                                                                                   |
|   test_configure_logging_file_handler()                                           |
|     - Use tmp_path fixture to create log file                                     |
|     - Verify logs are written to file                                             |
|                                                                                   |
|   test_configure_logging_invalid_file()                                           |
|     - Verify graceful handling of invalid file path                               |
|     - Should log warning to stderr, continue without file                         |
|                                                                                   |
|   test_get_logger_returns_configured_logger()                                     |
|     - Verify logger inherits from cast_highlight_mcp root                         |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: tests/unit/observability/test_metrics.py                                    |
+-----------------------------------------------------------------------------------+
| Purpose: Test metrics collection and export                                       |
| Coverage: metrics.py (100%)                                                       |
|                                                                                   |
| Test Cases:                                                                       |
|   test_record_tool_call_increments_counter()                                      |
|     - Verify calls_total increments                                               |
|                                                                                   |
|   test_record_tool_call_success_vs_error()                                        |
|     - Verify calls_success increments on success=True                             |
|     - Verify calls_error increments on success=False                              |
|                                                                                   |
|   test_record_tool_call_latency_histogram()                                       |
|     - Verify histogram buckets are populated correctly                            |
|     - Test boundary values (e.g., 0.01s, 0.1s, 1.0s)                              |
|                                                                                   |
|   test_record_tool_call_error_types()                                             |
|     - Verify errors_by_type dict is populated                                     |
|                                                                                   |
|   test_record_http_request()                                                      |
|     - Verify HTTP metrics are recorded                                            |
|     - Verify requests_by_status is populated                                      |
|                                                                                   |
|   test_export_json_format()                                                       |
|     - Verify JSON output matches expected schema                                  |
|     - Verify all tool metrics are included                                        |
|                                                                                   |
|   test_export_json_percentiles()                                                  |
|     - Verify p50, p95, p99 are calculated correctly                               |
|     - Use known histogram data to verify                                          |
|                                                                                   |
|   test_export_prometheus_format()                                                 |
|     - Verify Prometheus text format is valid                                      |
|     - Verify metric names include prefix                                          |
|                                                                                   |
|   test_metrics_reset_all()                                                        |
|     - Verify reset() clears all metrics                                           |
|                                                                                   |
|   test_metrics_reset_single_tool()                                                |
|     - Verify reset(tool_name="x") only resets that tool                           |
|                                                                                   |
|   test_metrics_disabled()                                                         |
|     - Verify no metrics recorded when enabled=False                               |
|                                                                                   |
|   test_metrics_thread_safety()                                                    |
|     - Use threading to call record_tool_call concurrently                         |
|     - Verify final counts are correct (no race conditions)                        |
|                                                                                   |
|   test_metrics_graceful_degradation()                                             |
|     - Inject exception in _update_histogram                                       |
|     - Verify no exception propagates to caller                                    |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: tests/unit/observability/test_config_observability.py                       |
+-----------------------------------------------------------------------------------+
| Purpose: Test observability configuration loading                                 |
| Coverage: config.py (observability portion)                                       |
|                                                                                   |
| Test Cases:                                                                       |
|   test_load_observability_config_defaults()                                       |
|     - Verify default values when no env vars set                                  |
|                                                                                   |
|   test_load_observability_config_custom_values()                                  |
|     - Set all env vars, verify they are loaded                                    |
|                                                                                   |
|   test_log_level_validation_valid()                                               |
|     - Test all valid log levels (DEBUG, INFO, etc.)                               |
|                                                                                   |
|   test_log_level_validation_invalid()                                             |
|     - Verify invalid level defaults to INFO with warning                          |
|                                                                                   |
|   test_log_level_case_insensitive()                                               |
|     - Verify "debug", "Debug", "DEBUG" all work                                   |
|                                                                                   |
|   test_parse_bool_true_values()                                                   |
|     - Test "true", "1", "yes", "on"                                               |
|                                                                                   |
|   test_parse_bool_false_values()                                                  |
|     - Test "false", "0", "no", "off", "", None                                    |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: tests/integration/test_observability_e2e.py                                 |
+-----------------------------------------------------------------------------------+
| Purpose: End-to-end observability testing                                         |
| Coverage: Full stack integration                                                  |
|                                                                                   |
| Test Cases:                                                                       |
|   test_tool_call_produces_logs(caplog)                                            |
|     - Mock API response                                                           |
|     - Call a tool through server                                                  |
|     - Verify "Tool call started" and "Tool call completed" in logs                |
|                                                                                   |
|   test_tool_call_produces_metrics()                                               |
|     - Mock API response                                                           |
|     - Call a tool through server                                                  |
|     - Verify metrics.get_metrics() shows correct counts                           |
|                                                                                   |
|   test_tool_error_logged_correctly(caplog)                                        |
|     - Mock API to return 404                                                      |
|     - Call tool                                                                   |
|     - Verify ERROR log with error_type="http_404"                                 |
|                                                                                   |
|   test_request_id_correlation()                                                   |
|     - Call tool                                                                   |
|     - Verify all log entries share same request_id                                |
|                                                                                   |
|   test_http_logging_in_client(caplog)                                             |
|     - Mock API response                                                           |
|     - Verify DEBUG logs for HTTP request/response                                 |
|                                                                                   |
|   test_server_lifecycle_logging(caplog)                                           |
|     - Start server                                                                |
|     - Verify "Server starting" and "Server ready" logs                            |
|                                                                                   |
|   test_observability_does_not_break_tool()                                        |
|     - Inject failure in logging (mock logger.info to raise)                       |
|     - Call tool                                                                   |
|     - Verify tool still returns correct result                                    |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
| File: tests/performance/test_observability_overhead.py                            |
+-----------------------------------------------------------------------------------+
| Purpose: Verify performance constraints from spec                                 |
| Coverage: NFR-001 (Performance Overhead)                                          |
|                                                                                   |
| Test Cases:                                                                       |
|   test_log_entry_overhead()                                                       |
|     - Time 1000 log entries                                                       |
|     - Verify average < 1ms per entry                                              |
|                                                                                   |
|   test_metric_increment_overhead()                                                |
|     - Time 10000 metric increments                                                |
|     - Verify average < 0.1ms per increment                                        |
|                                                                                   |
|   test_total_call_overhead()                                                      |
|     - Compare tool call with and without observability                            |
|     - Mock API to return instantly                                                |
|     - Verify overhead < 5ms (p99)                                                 |
|                                                                                   |
| Note: These tests may be marked @pytest.mark.slow                                 |
+-----------------------------------------------------------------------------------+
```

### Test Fixtures to Add

```python
# In tests/conftest.py (additions)

@pytest.fixture
def observability_config() -> ObservabilityConfig:
    """Create a test observability config."""
    return ObservabilityConfig(
        log_level="DEBUG",
        log_format="json",
        log_file=None,
        log_redact_ids=False,
        metrics_enabled=True,
        metrics_prefix="test",
        metrics_detailed=False,
    )

@pytest.fixture
def metrics_collector() -> MetricsCollector:
    """Create a fresh metrics collector for testing."""
    return MetricsCollector(prefix="test", enabled=True)

@pytest.fixture
def reset_global_metrics():
    """Reset global metrics before and after test."""
    from cast_highlight_mcp.observability.metrics import _metrics, get_metrics

    original = _metrics
    yield
    # Reset after test
    import cast_highlight_mcp.observability.metrics as m
    m._metrics = original

@pytest.fixture
def capture_logs(caplog):
    """Configure caplog for observability tests."""
    import logging
    caplog.set_level(logging.DEBUG, logger="cast_highlight_mcp")
    return caplog
```

### Test Coverage Requirements

```
+-----------------------------------------------------------------------------------+
| Module                                    | Min Coverage | Critical Paths         |
+-----------------------------------------------------------------------------------+
| observability/context.py                  | 100%         | request_context(),     |
|                                           |              | get_request_id()       |
+-----------------------------------------------------------------------------------+
| observability/logging.py                  | 95%          | format(),              |
|                                           |              | configure_logging()    |
+-----------------------------------------------------------------------------------+
| observability/metrics.py                  | 95%          | record_tool_call(),    |
|                                           |              | record_http_request(), |
|                                           |              | export_json()          |
+-----------------------------------------------------------------------------------+
| config.py (observability additions)       | 100%         | load_observability_    |
|                                           |              | config()               |
+-----------------------------------------------------------------------------------+
| server.py (observability additions)       | 90%          | call_tool() logging,   |
|                                           |              | main() initialization  |
+-----------------------------------------------------------------------------------+
| client.py (observability additions)       | 90%          | _request() logging     |
+-----------------------------------------------------------------------------------+
```

---

## 9. Implementation Phases

### Phase 1: Foundation (config.py + observability/context.py)
- Add ObservabilityConfig dataclass
- Add load_observability_config() function
- Create observability/context.py with RequestContext
- Unit tests for all above

### Phase 2: Logging Infrastructure (observability/logging.py)
- Create StructuredLogFormatter
- Create TextLogFormatter
- Create configure_logging()
- Create get_logger()
- Add redaction logic
- Unit tests for formatters and configuration

### Phase 3: Metrics Infrastructure (observability/metrics.py)
- Create ToolMetrics and HttpMetrics dataclasses
- Create MetricsCollector class
- Implement histogram logic
- Implement JSON export
- Implement Prometheus export (basic, no dependency)
- Unit tests for metrics collection and export

### Phase 4: Server Integration (server.py)
- Import observability modules
- Modify main() to initialize observability
- Modify call_tool() to use request_context
- Add tool call logging and metrics
- Add server lifecycle logging
- Integration tests

### Phase 5: Client Integration (client.py)
- Replace basic logger with structured logger
- Modify _request() for HTTP logging and metrics
- Update list_domains() to use new logging pattern
- Integration tests

### Phase 6: Documentation and Final Testing
- Update CLAUDE.md with new environment variables
- Run full test suite
- Performance benchmarks
- Security review (redaction verification)

---

## 10. Appendix: Error Classification

```python
# Error type classification for metrics

def classify_error(exception: Exception) -> str:
    """Classify an exception for metrics tracking."""
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        if 400 <= status < 500:
            return f"http_{status}"  # e.g., "http_404"
        elif 500 <= status < 600:
            return f"http_{status}"  # e.g., "http_500"
    elif isinstance(exception, httpx.TimeoutException):
        return "timeout"
    elif isinstance(exception, httpx.ConnectError):
        return "connection"
    elif isinstance(exception, ValueError):
        return "validation"
    return "unknown"
```

---

## 11. Appendix: Redaction Patterns

```python
# Sensitive data patterns for redaction

REDACT_PATTERNS = {
    "access_token": r"[A-Za-z0-9_-]{20,}",
    "authorization": r"Bearer\s+[A-Za-z0-9_-]+",
    "api_key": r"[A-Za-z0-9_-]{32,}",
}

def _redact_sensitive(context: dict, redact_ids: bool = False) -> dict:
    """Redact sensitive values from log context."""
    result = {}
    for key, value in context.items():
        key_lower = key.lower()

        # Always redact tokens and auth headers
        if "token" in key_lower or "authorization" in key_lower or "api_key" in key_lower:
            result[key] = "[REDACTED]"
        # Optionally redact IDs
        elif redact_ids and ("_id" in key_lower or key_lower == "id"):
            result[key] = "[REDACTED]"
        else:
            result[key] = value

    return result
```
