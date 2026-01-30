# SPARC Pseudocode: Structured Logging Module

> **Document Version**: 1.0.0
> **Status**: Draft
> **Related Spec**: OBSERVABILITY-SPEC.md (Sections 2.1, 5.1)
> **Author**: SPARC Pseudocode Agent
> **Date**: 2026-01-29

---

## 1. Overview

This document provides implementation-ready pseudocode for the structured logging subsystem of the cast-highlight-mcp observability feature. The pseudocode is Python-like and detailed enough for direct implementation.

### 1.1 Module Structure

```
src/cast_highlight_mcp/observability/
    __init__.py          # Package exports
    logging.py           # StructuredLogFormatter, configure_logging
    context.py           # log_context context manager, LogContext
    redaction.py         # RedactionFilter, sensitive data handling
```

---

## 2. Data Structures

### 2.1 LogContext Dataclass

```python
DATACLASS: LogContext
PURPOSE: Holds structured context for correlated log entries

FIELDS:
    request_id: str                      # Unique identifier for request correlation
    tool_name: str | None = None         # MCP tool being invoked
    duration_ms: float | None = None     # Operation duration in milliseconds
    success: bool | None = None          # Whether operation succeeded
    error_type: str | None = None        # Exception class name if error
    error_message: str | None = None     # Error description if error
    http_method: str | None = None       # HTTP method (GET, POST, etc.)
    http_path: str | None = None         # URL path (not full URL)
    http_status: int | None = None       # HTTP response status code
    response_size_bytes: int | None = None  # Response payload size
    extra: dict[str, Any] = field(default_factory=dict)  # Additional context

METHODS:
    to_dict() -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        FOR EACH field IN self.fields:
            value = getattr(self, field.name)
            IF value IS NOT None:
                IF field.name == "extra":
                    result.update(value)
                ELSE:
                    result[field.name] = value
        RETURN result
```

### 2.2 ObservabilityConfig Dataclass

```python
DATACLASS: ObservabilityConfig
PURPOSE: Configuration for logging behavior

FIELDS:
    log_level: str = "INFO"              # Minimum log level
    log_format: str = "json"             # Output format: "json" or "text"
    log_file: str | None = None          # Optional file path for log output
    log_redact_ids: bool = False         # Whether to redact company/app IDs

METHODS:
    @classmethod
    from_env() -> ObservabilityConfig:
        """Load configuration from environment variables."""
        RETURN ObservabilityConfig(
            log_level=os.getenv("HIGHLIGHT_LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("HIGHLIGHT_LOG_FORMAT", "json").lower(),
            log_file=os.getenv("HIGHLIGHT_LOG_FILE"),
            log_redact_ids=os.getenv("HIGHLIGHT_LOG_REDACT_IDS", "false").lower() == "true"
        )

    validate() -> None:
        """Validate configuration values."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        IF self.log_level NOT IN valid_levels:
            logger.warning(
                "Invalid log level '%s', defaulting to INFO",
                self.log_level
            )
            self.log_level = "INFO"

        valid_formats = {"json", "text"}
        IF self.log_format NOT IN valid_formats:
            logger.warning(
                "Invalid log format '%s', defaulting to json",
                self.log_format
            )
            self.log_format = "json"
```

---

## 3. StructuredLogFormatter Class

### 3.1 Class Definition

```python
CLASS: StructuredLogFormatter
INHERITS: logging.Formatter
PURPOSE: Format log records as JSON for machine parsing

CONSTANTS:
    DEFAULT_FIELDS = ["timestamp", "level", "logger", "message"]
    TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"

ATTRIBUTES:
    include_context: bool           # Whether to include context object
    redact_ids: bool                # Whether to redact IDs in output
```

### 3.2 Constructor

```python
METHOD: __init__(self, include_context: bool = True, redact_ids: bool = False)
PURPOSE: Initialize formatter with configuration

ALGORITHM:
BEGIN
    # Call parent constructor (no format string needed for JSON)
    super().__init__()

    self.include_context = include_context
    self.redact_ids = redact_ids
END
```

### 3.3 Format Method

```python
METHOD: format(self, record: logging.LogRecord) -> str
PURPOSE: Convert log record to JSON string
INPUT: record - Python logging LogRecord object
OUTPUT: JSON-formatted string

ALGORITHM:
BEGIN
    # Build base log entry
    entry = {
        "timestamp": self._format_timestamp(record.created),
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage()
    }

    # Add context if present and enabled
    IF self.include_context AND hasattr(record, "context"):
        context = record.context
        IF isinstance(context, LogContext):
            context = context.to_dict()

        # Apply redaction if configured
        IF self.redact_ids:
            context = self._redact_context(context)

        IF context:  # Only add non-empty context
            entry["context"] = context

    # Add exception info if present
    IF record.exc_info IS NOT None:
        entry["exception"] = self._format_exception(record.exc_info)

    # Serialize to JSON
    TRY:
        RETURN json.dumps(entry, default=str, ensure_ascii=False)
    EXCEPT (TypeError, ValueError) AS e:
        # Fallback for non-serializable objects
        entry["message"] = f"{record.getMessage()} [JSON serialization failed: {e}]"
        entry.pop("context", None)
        RETURN json.dumps(entry)
END
```

### 3.4 Helper Methods

```python
METHOD: _format_timestamp(self, created: float) -> str
PURPOSE: Convert Unix timestamp to ISO 8601 format with milliseconds
INPUT: created - Unix timestamp from LogRecord
OUTPUT: ISO 8601 formatted string

ALGORITHM:
BEGIN
    dt = datetime.datetime.fromtimestamp(created, tz=datetime.timezone.utc)
    # Format with milliseconds
    base = dt.strftime(self.TIMESTAMP_FORMAT)
    ms = int((created % 1) * 1000)
    RETURN f"{base}.{ms:03d}Z"
END


METHOD: _format_exception(self, exc_info: tuple) -> dict
PURPOSE: Format exception information for JSON output
INPUT: exc_info - (type, value, traceback) tuple
OUTPUT: Dictionary with exception details

ALGORITHM:
BEGIN
    IF exc_info IS None OR exc_info[0] IS None:
        RETURN None

    exc_type, exc_value, exc_tb = exc_info
    RETURN {
        "type": exc_type.__name__,
        "message": str(exc_value),
        "traceback": traceback.format_exception(exc_type, exc_value, exc_tb)
    }
END


METHOD: _redact_context(self, context: dict) -> dict
PURPOSE: Redact sensitive IDs from context dictionary
INPUT: context - Original context dictionary
OUTPUT: Context with IDs redacted

ALGORITHM:
BEGIN
    redacted = context.copy()

    # Fields to redact when redact_ids is enabled
    id_fields = ["company_id", "domain_id", "application_id", "app_id"]

    FOR EACH field IN id_fields:
        IF field IN redacted:
            redacted[field] = "[REDACTED_ID]"

    # Handle nested arguments
    IF "arguments" IN redacted AND isinstance(redacted["arguments"], dict):
        redacted["arguments"] = self._redact_context(redacted["arguments"])

    RETURN redacted
END
```

---

## 4. TextLogFormatter Class

### 4.1 Class Definition

```python
CLASS: TextLogFormatter
INHERITS: logging.Formatter
PURPOSE: Format log records as human-readable text

ATTRIBUTES:
    redact_ids: bool
```

### 4.2 Format Method

```python
METHOD: format(self, record: logging.LogRecord) -> str
PURPOSE: Convert log record to human-readable text
INPUT: record - Python logging LogRecord object
OUTPUT: Formatted text string

ALGORITHM:
BEGIN
    # Format: "2026-01-29 12:34:56.789 INFO  [logger.name] Message key=value key=value"
    timestamp = self._format_timestamp(record.created)
    level = f"{record.levelname:<5}"  # Left-align, pad to 5 chars
    logger_name = record.name

    # Build base message
    parts = [timestamp, level, f"[{logger_name}]", record.getMessage()]

    # Append context fields as key=value pairs
    IF hasattr(record, "context"):
        context = record.context
        IF isinstance(context, LogContext):
            context = context.to_dict()

        IF self.redact_ids:
            context = self._redact_context(context)

        FOR EACH key, value IN context.items():
            # Format value appropriately
            IF isinstance(value, str):
                formatted_value = value
            ELIF isinstance(value, bool):
                formatted_value = str(value).lower()
            ELIF isinstance(value, float):
                formatted_value = f"{value:.2f}"
            ELSE:
                formatted_value = str(value)

            parts.append(f"{key}={formatted_value}")

    RETURN " ".join(parts)
END


METHOD: _format_timestamp(self, created: float) -> str
PURPOSE: Format timestamp for text output
INPUT: created - Unix timestamp
OUTPUT: Formatted timestamp string

ALGORITHM:
BEGIN
    dt = datetime.datetime.fromtimestamp(created, tz=datetime.timezone.utc)
    base = dt.strftime("%Y-%m-%d %H:%M:%S")
    ms = int((created % 1) * 1000)
    RETURN f"{base}.{ms:03d}"
END
```

---

## 5. RedactionFilter Class

### 5.1 Class Definition

```python
CLASS: RedactionFilter
INHERITS: logging.Filter
PURPOSE: Filter and redact sensitive data from all log records before output

CONSTANTS:
    SENSITIVE_PATTERNS = [
        (re.compile(r'Bearer\s+[A-Za-z0-9\-_\.]+'), 'Bearer [REDACTED]'),
        (re.compile(r'access_token["\']?\s*[:=]\s*["\']?[^"\'&\s]+'), 'access_token=[REDACTED]'),
        (re.compile(r'Authorization["\']?\s*[:=]\s*["\']?[^"\'&\s]+'), 'Authorization=[REDACTED]'),
        (re.compile(r'token["\']?\s*[:=]\s*["\']?[A-Za-z0-9\-_\.]{20,}'), 'token=[REDACTED]'),
    ]

    SENSITIVE_KEYS = frozenset([
        "access_token",
        "authorization",
        "token",
        "api_key",
        "apikey",
        "secret",
        "password",
        "credential",
    ])
```

### 5.2 Filter Method

```python
METHOD: filter(self, record: logging.LogRecord) -> bool
PURPOSE: Apply redaction to log record, always returns True (allows all records)
INPUT: record - LogRecord to process
OUTPUT: True (always, filter is for transformation not filtering)

ALGORITHM:
BEGIN
    # Redact message string
    record.msg = self._redact_string(record.msg)

    # Redact arguments if present
    IF record.args:
        IF isinstance(record.args, dict):
            record.args = self._redact_dict(record.args)
        ELIF isinstance(record.args, tuple):
            record.args = tuple(
                self._redact_value(arg) FOR arg IN record.args
            )

    # Redact context if present
    IF hasattr(record, "context"):
        IF isinstance(record.context, dict):
            record.context = self._redact_dict(record.context)
        ELIF isinstance(record.context, LogContext):
            # Redact extra dict within LogContext
            record.context.extra = self._redact_dict(record.context.extra)

    RETURN True  # Always allow record through
END
```

### 5.3 Redaction Helper Methods

```python
METHOD: _redact_string(self, value: str) -> str
PURPOSE: Apply regex patterns to redact sensitive data in strings
INPUT: value - String to redact
OUTPUT: Redacted string

ALGORITHM:
BEGIN
    IF NOT isinstance(value, str):
        RETURN value

    result = value
    FOR EACH pattern, replacement IN self.SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)

    RETURN result
END


METHOD: _redact_dict(self, data: dict) -> dict
PURPOSE: Recursively redact sensitive keys in dictionaries
INPUT: data - Dictionary to redact
OUTPUT: Redacted dictionary (new copy)

ALGORITHM:
BEGIN
    result = {}

    FOR EACH key, value IN data.items():
        key_lower = key.lower()

        IF key_lower IN self.SENSITIVE_KEYS:
            result[key] = "[REDACTED]"
        ELIF isinstance(value, dict):
            result[key] = self._redact_dict(value)
        ELIF isinstance(value, list):
            result[key] = [self._redact_value(item) FOR item IN value]
        ELIF isinstance(value, str):
            result[key] = self._redact_string(value)
        ELSE:
            result[key] = value

    RETURN result
END


METHOD: _redact_value(self, value: Any) -> Any
PURPOSE: Redact a single value based on its type
INPUT: value - Any value
OUTPUT: Redacted value

ALGORITHM:
BEGIN
    IF isinstance(value, dict):
        RETURN self._redact_dict(value)
    ELIF isinstance(value, str):
        RETURN self._redact_string(value)
    ELIF isinstance(value, list):
        RETURN [self._redact_value(item) FOR item IN value]
    ELSE:
        RETURN value
END
```

---

## 6. configure_logging() Function

### 6.1 Function Signature

```python
FUNCTION: configure_logging(config: ObservabilityConfig | None = None) -> None
PURPOSE: Configure the logging system based on settings
INPUT: config - ObservabilityConfig instance (loads from env if None)
OUTPUT: None (configures global logging state)
```

### 6.2 Algorithm

```python
ALGORITHM: configure_logging

BEGIN
    # Load config from environment if not provided
    IF config IS None:
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
    IF config.log_format == "json":
        formatter = StructuredLogFormatter(
            include_context=True,
            redact_ids=config.log_redact_ids
        )
    ELSE:
        formatter = TextLogFormatter(
            redact_ids=config.log_redact_ids
        )

    # Create console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Add redaction filter to console handler
    redaction_filter = RedactionFilter()
    console_handler.addFilter(redaction_filter)

    root_logger.addHandler(console_handler)

    # Add file handler if configured
    IF config.log_file:
        TRY:
            file_handler = logging.FileHandler(
                config.log_file,
                mode='a',  # Append mode
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            file_handler.addFilter(redaction_filter)
            root_logger.addHandler(file_handler)
        EXCEPT (IOError, OSError) AS e:
            # Log to stderr but don't fail
            sys.stderr.write(f"Warning: Could not open log file '{config.log_file}': {e}\n")

    # Prevent propagation to root logger to avoid duplicate logs
    root_logger.propagate = False

    # Log configuration complete (at DEBUG level to avoid noise)
    root_logger.debug(
        "Logging configured",
        extra={"context": {
            "log_level": config.log_level,
            "log_format": config.log_format,
            "log_file": config.log_file or "(none)"
        }}
    )
END
```

---

## 7. log_context() Context Manager

### 7.1 Function Signature

```python
FUNCTION: log_context(request_id: str | None = None, **kwargs) -> Generator[LogContext, None, None]
PURPOSE: Provide correlated logging context for a request/operation
INPUT:
    request_id - Unique request identifier (auto-generated if None)
    **kwargs - Additional context fields to include
OUTPUT: Yields LogContext instance
```

### 7.2 Algorithm

```python
ALGORITHM: log_context
USES: contextvars for thread-safe context storage

# Module-level context variable
_current_context: contextvars.ContextVar[LogContext | None] = contextvars.ContextVar(
    'log_context',
    default=None
)


@contextmanager
FUNCTION: log_context(request_id: str | None = None, **kwargs)

BEGIN
    # Generate request ID if not provided
    IF request_id IS None:
        request_id = str(uuid.uuid4())[:8]  # Short UUID for readability

    # Create context object
    context = LogContext(
        request_id=request_id,
        **kwargs
    )

    # Store in context variable
    token = _current_context.set(context)

    TRY:
        YIELD context
    FINALLY:
        # Restore previous context (or None)
        _current_context.reset(token)
END


FUNCTION: get_current_context() -> LogContext | None
PURPOSE: Get the current log context from any code location
OUTPUT: Current LogContext or None if not in a context

BEGIN
    RETURN _current_context.get()
END
```

### 7.3 Context-Aware Logger Adapter

```python
CLASS: ContextAwareLogger
INHERITS: logging.LoggerAdapter
PURPOSE: Automatically inject current context into log records

METHODS:

METHOD: process(self, msg: str, kwargs: dict) -> tuple[str, dict]
PURPOSE: Add context to log record
INPUT: msg - Log message, kwargs - Additional log arguments
OUTPUT: Processed (msg, kwargs) tuple

ALGORITHM:
BEGIN
    # Get current context
    context = get_current_context()

    IF context IS NOT None:
        # Merge with any existing extra context
        extra = kwargs.get("extra", {})

        IF "context" IN extra AND isinstance(extra["context"], dict):
            # Merge provided context with current context
            merged = context.to_dict()
            merged.update(extra["context"])
            extra["context"] = merged
        ELSE:
            extra["context"] = context.to_dict()

        kwargs["extra"] = extra

    RETURN msg, kwargs
END


FUNCTION: get_logger(name: str) -> ContextAwareLogger
PURPOSE: Get a context-aware logger for a module
INPUT: name - Logger name (typically __name__)
OUTPUT: ContextAwareLogger wrapping the standard logger

BEGIN
    base_logger = logging.getLogger(name)
    RETURN ContextAwareLogger(base_logger, {})
END
```

---

## 8. Integration Points

### 8.1 Server Integration (server.py)

```python
# At module level, after imports
from .observability import get_logger, configure_logging, log_context
from .observability.context import LogContext

logger = get_logger(__name__)


# In main() function, before server starts
FUNCTION: main()
BEGIN
    # Configure logging first
    configure_logging()

    logger.info(
        "Server starting",
        extra={"context": {
            "version": "0.1.0",
            "server_name": "cast-highlight-mcp"
        }}
    )

    # ... rest of main()
END


# In call_tool() handler
@server.call_tool()
ASYNC FUNCTION: call_tool(name: str, arguments: dict) -> list[TextContent]
BEGIN
    # Generate unique request ID for this tool call
    request_id = str(uuid.uuid4())[:8]

    # Record start time
    start_time = time.perf_counter()

    # Enter log context for correlation
    WITH log_context(request_id=request_id, tool_name=name):

        # Log tool call start
        logger.info(
            "Tool call started",
            extra={"context": {"arguments": arguments}}  # DEBUG level would include this
        )

        TRY:
            api = get_client()

            # ... existing tool dispatch logic ...

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log success
            logger.info(
                "Tool call completed",
                extra={"context": {
                    "duration_ms": round(duration_ms, 2),
                    "success": True,
                    "response_size_bytes": len(json.dumps(result))
                }}
            )

            RETURN [TextContent(type="text", text=json.dumps(result, indent=2))]

        EXCEPT Exception AS e:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Determine error type
            error_type = type(e).__name__

            # Log failure
            logger.error(
                "Tool call failed",
                extra={"context": {
                    "duration_ms": round(duration_ms, 2),
                    "success": False,
                    "error_type": error_type,
                    "error_message": str(e)
                }},
                exc_info=True  # Include traceback at ERROR level
            )

            RETURN [TextContent(type="text", text=f"Error: {str(e)}")]
END
```

### 8.2 Client Integration (client.py)

```python
# At module level, replace existing logging import
from .observability import get_logger
from .observability.context import get_current_context

logger = get_logger(__name__)


# In _request() method
ASYNC METHOD: _request(self, method: str, path: str, **kwargs) -> Any
BEGIN
    # Get current context for correlation
    ctx = get_current_context()
    request_id = ctx.request_id IF ctx ELSE "no-context"

    # Log request start (DEBUG level)
    logger.debug(
        "HTTP request started",
        extra={"context": {
            "method": method,
            "path": path,
            "request_id": request_id
        }}
    )

    start_time = time.perf_counter()

    TRY:
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        response = await client.request(method, url, **kwargs)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000
        status_code = response.status_code

        # Determine log level based on status code
        IF 200 <= status_code < 300:
            log_level = logging.DEBUG
        ELIF 400 <= status_code < 500:
            log_level = logging.WARNING
        ELSE:  # 5xx
            log_level = logging.ERROR

        logger.log(
            log_level,
            "HTTP request completed",
            extra={"context": {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "request_id": request_id
            }}
        )

        response.raise_for_status()
        RETURN response.json()

    EXCEPT httpx.TimeoutException AS e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(
            "HTTP request timeout",
            extra={"context": {
                "method": method,
                "path": path,
                "duration_ms": round(duration_ms, 2),
                "error_type": "timeout",
                "request_id": request_id
            }}
        )
        RAISE

    EXCEPT httpx.HTTPStatusError AS e:
        # Already logged above, just re-raise
        RAISE

    EXCEPT httpx.RequestError AS e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "HTTP request failed",
            extra={"context": {
                "method": method,
                "path": path,
                "duration_ms": round(duration_ms, 2),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "request_id": request_id
            }}
        )
        RAISE
END
```

### 8.3 Lifecycle Logging

```python
# Server startup sequence in server.py main()

ASYNC FUNCTION: run()
BEGIN
    global _client

    # Log server starting
    logger.info(
        "Server starting",
        extra={"context": {
            "version": __version__,
            "base_url": config.base_url  # Redacted by filter if sensitive
        }}
    )

    TRY:
        ASYNC WITH AsyncExitStack() AS stack:
            # Initialize client
            config = load_config()
            _client = await stack.enter_async_context(HighlightClient(config))

            # Log ready state
            logger.info(
                "Server ready",
                extra={"context": {
                    "tools_count": len(TOOLS),
                    "company_id": config.company_id  # Redacted if configured
                }}
            )

            # Run server
            read_stream, write_stream = await stack.enter_async_context(stdio_server())
            await server.run(read_stream, write_stream, server.create_initialization_options())

    EXCEPT Exception AS e:
        logger.critical(
            "Server failed to start",
            extra={"context": {
                "error_type": type(e).__name__,
                "error_message": str(e)
            }},
            exc_info=True
        )
        RAISE

    FINALLY:
        logger.info("Server shutdown")
END
```

---

## 9. Complexity Analysis

### 9.1 Time Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `StructuredLogFormatter.format()` | O(n) | n = context fields |
| `RedactionFilter.filter()` | O(m*p) | m = message length, p = patterns |
| `log_context()` enter/exit | O(1) | Context variable operations |
| `LogContext.to_dict()` | O(k) | k = number of fields |
| `configure_logging()` | O(1) | One-time setup |

### 9.2 Space Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Log entry creation | O(n) | n = message + context size |
| Redaction filter | O(m) | m = input string length (creates copy) |
| Context storage | O(c) | c = concurrent contexts (one per async task) |

### 9.3 Performance Considerations

1. **Lazy Evaluation**: Use `logger.isEnabledFor(level)` before expensive context building
2. **String Formatting**: Avoid f-strings in log messages; use % formatting for deferred evaluation
3. **Async Safety**: contextvars is async-safe, no locking required
4. **Memory**: LogContext objects are lightweight dataclasses

---

## 10. Error Handling Strategy

### 10.1 Graceful Degradation

```python
# All logging operations should be wrapped to prevent failures from affecting tool execution

FUNCTION: safe_log(logger, level, msg, **kwargs)
PURPOSE: Log without raising exceptions
BEGIN
    TRY:
        logger.log(level, msg, **kwargs)
    EXCEPT Exception AS e:
        # Last resort: write to stderr
        TRY:
            sys.stderr.write(f"Logging failed: {e}\n")
        EXCEPT:
            PASS  # Truly silent failure
END
```

### 10.2 Formatter Error Recovery

```python
# In StructuredLogFormatter.format()

TRY:
    RETURN json.dumps(entry, default=str, ensure_ascii=False)
EXCEPT (TypeError, ValueError, RecursionError) AS e:
    # Fallback to minimal entry
    fallback = {
        "timestamp": entry.get("timestamp", "unknown"),
        "level": entry.get("level", "ERROR"),
        "logger": entry.get("logger", "unknown"),
        "message": f"[Log serialization failed: {e}] {str(record.msg)[:200]}"
    }
    RETURN json.dumps(fallback)
```

---

## 11. Test Scenarios

### 11.1 Unit Test Cases

```python
# Test StructuredLogFormatter
TEST: "JSON formatter produces valid JSON"
    record = create_log_record("Test message", level=INFO)
    formatter = StructuredLogFormatter()
    output = formatter.format(record)
    ASSERT json.loads(output) is valid
    ASSERT output contains "timestamp"
    ASSERT output contains "level": "INFO"

TEST: "Formatter includes context when present"
    record = create_log_record("Test", context={"tool_name": "test_tool"})
    formatter = StructuredLogFormatter()
    output = json.loads(formatter.format(record))
    ASSERT output["context"]["tool_name"] == "test_tool"

TEST: "Formatter handles non-serializable objects"
    record = create_log_record("Test", context={"obj": object()})
    formatter = StructuredLogFormatter()
    output = formatter.format(record)  # Should not raise
    ASSERT output is valid JSON string

# Test RedactionFilter
TEST: "Filter redacts bearer tokens"
    record = create_log_record("Token: Bearer abc123xyz")
    filter = RedactionFilter()
    filter.filter(record)
    ASSERT "abc123xyz" NOT IN record.msg
    ASSERT "[REDACTED]" IN record.msg

TEST: "Filter redacts sensitive dictionary keys"
    record = create_log_record("Data", context={"access_token": "secret123"})
    filter = RedactionFilter()
    filter.filter(record)
    ASSERT record.context["access_token"] == "[REDACTED]"

# Test log_context
TEST: "Context manager sets and clears context"
    ASSERT get_current_context() IS None
    WITH log_context(request_id="test-123") AS ctx:
        ASSERT get_current_context() IS NOT None
        ASSERT ctx.request_id == "test-123"
    ASSERT get_current_context() IS None

TEST: "Nested contexts work correctly"
    WITH log_context(request_id="outer") AS outer:
        ASSERT get_current_context().request_id == "outer"
        WITH log_context(request_id="inner") AS inner:
            ASSERT get_current_context().request_id == "inner"
        ASSERT get_current_context().request_id == "outer"
```

### 11.2 Integration Test Cases

```python
TEST: "Tool call logging produces correlated entries"
    # Capture log output
    WITH capture_logs() AS logs:
        await call_tool("highlight_get_company", {})

    # Verify correlation
    entries = [json.loads(line) FOR line IN logs]
    request_ids = {e["context"]["request_id"] FOR e IN entries}
    ASSERT len(request_ids) == 1  # All entries have same request_id

    # Verify sequence
    ASSERT entries[0]["message"] == "Tool call started"
    ASSERT entries[-1]["message"] IN ("Tool call completed", "Tool call failed")

TEST: "HTTP client logging respects log levels"
    configure_logging(ObservabilityConfig(log_level="WARNING"))

    WITH capture_logs() AS logs:
        await client._request("GET", "/companies/123")

    # DEBUG logs should not appear
    ASSERT NOT any("HTTP request started" IN line FOR line IN logs)
```

---

## 12. Implementation Checklist

- [ ] Create `src/cast_highlight_mcp/observability/` package
- [ ] Implement `LogContext` dataclass in `context.py`
- [ ] Implement `StructuredLogFormatter` in `logging.py`
- [ ] Implement `TextLogFormatter` in `logging.py`
- [ ] Implement `RedactionFilter` in `redaction.py`
- [ ] Implement `configure_logging()` in `logging.py`
- [ ] Implement `log_context()` context manager in `context.py`
- [ ] Implement `get_logger()` function in `__init__.py`
- [ ] Add `ObservabilityConfig` to `config.py`
- [ ] Integrate logging into `server.py`
- [ ] Integrate logging into `client.py`
- [ ] Write unit tests for all formatters and filters
- [ ] Write integration tests for correlated logging
- [ ] Update `__init__.py` exports

---

## References

- OBSERVABILITY-SPEC.md Section 2.1 (Structured Logging)
- OBSERVABILITY-SPEC.md Section 5.1 (Logging API)
- Python logging module documentation
- PEP 567 (contextvars)
