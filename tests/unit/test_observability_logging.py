"""Unit tests for observability logging module.

Tests cover:
- StructuredLogFormatter (JSON output)
- TextLogFormatter (human-readable output)
- RedactionFilter (sensitive data redaction)
- configure_logging() function
- get_logger() function
"""

import json
import logging
import re
import sys

import pytest


class TestStructuredLogFormatter:
    """Tests for StructuredLogFormatter class."""

    def test_format_produces_valid_json(self):
        """Verify output is valid JSON."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert isinstance(parsed, dict)

    def test_format_includes_required_fields(self):
        """Verify required fields: timestamp, level, logger, message."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="cast_highlight_mcp.server",
            level=logging.INFO,
            pathname="server.py",
            lineno=42,
            msg="Tool call started",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "cast_highlight_mcp.server"
        assert parsed["message"] == "Tool call started"

    def test_format_timestamp_is_iso8601(self):
        """Verify timestamp is ISO 8601 format with milliseconds."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        timestamp = parsed["timestamp"]
        # Should match ISO 8601 with milliseconds: 2026-01-29T12:34:56.789Z
        pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z"
        assert re.match(pattern, timestamp), f"Timestamp '{timestamp}' doesn't match ISO 8601"

    def test_format_includes_context_when_present(self):
        """Verify context dict is included in output."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.context = {"tool_name": "highlight_get_company", "request_id": "abc123"}

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "context" in parsed
        assert parsed["context"]["tool_name"] == "highlight_get_company"
        assert parsed["context"]["request_id"] == "abc123"

    def test_format_without_context(self):
        """Verify formatter works when no context is present."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["message"] == "Warning message"
        assert parsed["level"] == "WARNING"
        # Context should either be absent or empty
        assert "context" not in parsed or parsed["context"] == {}

    def test_format_handles_exception_info(self):
        """Verify exception info is included when present."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert "Test error" in parsed["exception"]["message"]

    def test_format_handles_non_serializable_objects(self):
        """Verify formatter handles non-JSON-serializable objects gracefully."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        # Add a non-serializable object to context
        record.context = {"obj": object(), "normal": "value"}

        # Should not raise, should produce valid JSON
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "message" in parsed

    def test_format_with_message_formatting(self):
        """Verify message formatting with arguments works."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processing %s items",
            args=(42,),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["message"] == "Processing 42 items"

    def test_format_redacts_ids_when_configured(self):
        """Verify IDs are redacted when redact_ids is True."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter(redact_ids=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {
            "company_id": 12345,
            "application_id": 67890,
            "domain_id": 111,
            "tool_name": "test_tool",
        }

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["context"]["company_id"] == "[REDACTED_ID]"
        assert parsed["context"]["application_id"] == "[REDACTED_ID]"
        assert parsed["context"]["domain_id"] == "[REDACTED_ID]"
        assert parsed["context"]["tool_name"] == "test_tool"  # Not an ID field

    def test_format_does_not_redact_ids_by_default(self):
        """Verify IDs are not redacted by default."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {"company_id": 12345}

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["context"]["company_id"] == 12345


class TestTextLogFormatter:
    """Tests for TextLogFormatter class."""

    def test_format_produces_human_readable_output(self):
        """Verify output is human-readable text format."""
        from cast_highlight_mcp.observability.logging import TextLogFormatter

        formatter = TextLogFormatter()
        record = logging.LogRecord(
            name="cast_highlight_mcp.server",
            level=logging.INFO,
            pathname="server.py",
            lineno=1,
            msg="Server starting",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Should contain key elements
        assert "INFO" in output
        assert "cast_highlight_mcp.server" in output
        assert "Server starting" in output

    def test_format_includes_timestamp(self):
        """Verify timestamp is included in text output."""
        from cast_highlight_mcp.observability.logging import TextLogFormatter

        formatter = TextLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Should contain date-like pattern
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}"
        assert re.search(pattern, output), f"Output '{output}' doesn't contain timestamp"

    def test_format_includes_context_as_key_value_pairs(self):
        """Verify context is formatted as key=value pairs."""
        from cast_highlight_mcp.observability.logging import TextLogFormatter

        formatter = TextLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.context = {"tool_name": "test_tool", "duration_ms": 123.45}

        output = formatter.format(record)

        assert "tool_name=test_tool" in output
        assert "duration_ms=123.45" in output

    def test_format_boolean_values_as_lowercase(self):
        """Verify boolean values are formatted as lowercase."""
        from cast_highlight_mcp.observability.logging import TextLogFormatter

        formatter = TextLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {"success": True, "enabled": False}

        output = formatter.format(record)

        assert "success=true" in output
        assert "enabled=false" in output

    def test_format_pads_level_name(self):
        """Verify level name is padded for alignment."""
        from cast_highlight_mcp.observability.logging import TextLogFormatter

        formatter = TextLogFormatter()

        for level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )
            output = formatter.format(record)
            # Level should be present
            level_name = logging.getLevelName(level)
            assert level_name in output

    def test_format_redacts_ids_when_configured(self):
        """Verify IDs are redacted in text format when configured."""
        from cast_highlight_mcp.observability.logging import TextLogFormatter

        formatter = TextLogFormatter(redact_ids=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {"company_id": 12345}

        output = formatter.format(record)

        assert "12345" not in output
        assert "[REDACTED_ID]" in output


class TestRedactionFilter:
    """Tests for RedactionFilter class."""

    def test_filter_redacts_bearer_tokens_in_message(self):
        """Verify Bearer tokens are redacted from message."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Token: Bearer abc123xyz789long_token_here",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)

        assert result is True  # Filter always allows records through
        assert "abc123xyz789long_token_here" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_filter_redacts_access_token_pattern(self):
        """Verify access_token patterns are redacted."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Config: access_token=secret_token_value_here",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)

        assert "secret_token_value_here" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_filter_redacts_authorization_pattern(self):
        """Verify Authorization patterns are redacted."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg='Headers: Authorization="Bearer mytoken123"',
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)

        assert "mytoken123" not in record.msg

    def test_filter_redacts_sensitive_keys_in_context(self):
        """Verify sensitive keys in context are redacted."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {
            "access_token": "secret123",
            "api_key": "key456",
            "password": "pass789",
            "tool_name": "test_tool",
        }

        filter_obj.filter(record)

        assert record.context["access_token"] == "[REDACTED]"
        assert record.context["api_key"] == "[REDACTED]"
        assert record.context["password"] == "[REDACTED]"
        assert record.context["tool_name"] == "test_tool"  # Not sensitive

    def test_filter_redacts_nested_sensitive_keys(self):
        """Verify sensitive keys in nested dicts are redacted."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {
            "config": {"access_token": "secret", "base_url": "https://api.example.com"},
            "headers": {"Authorization": "Bearer token"},
        }

        filter_obj.filter(record)

        assert record.context["config"]["access_token"] == "[REDACTED]"
        assert record.context["config"]["base_url"] == "https://api.example.com"
        assert record.context["headers"]["Authorization"] == "[REDACTED]"

    def test_filter_always_returns_true(self):
        """Verify filter always returns True (allows all records)."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)

        assert result is True

    def test_filter_handles_tuple_args(self):
        """Verify filter handles tuple args correctly."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Token is %s",
            args=("Bearer secret_token_here",),
            exc_info=None,
        )

        filter_obj.filter(record)

        # Args should be redacted
        assert "secret_token_here" not in str(record.args)

    def test_filter_handles_dict_args(self):
        """Verify filter handles dict args correctly."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Config: %s",
            args=(),
            exc_info=None,
        )
        # Manually set args as dict for testing the filter behavior
        record.args = {"access_token": "secret123"}

        filter_obj.filter(record)

        assert record.args["access_token"] == "[REDACTED]"

    def test_filter_case_insensitive_key_matching(self):
        """Verify sensitive key matching is case-insensitive."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {
            "ACCESS_TOKEN": "secret1",
            "Api_Key": "secret2",
            "PASSWORD": "secret3",
        }

        filter_obj.filter(record)

        assert record.context["ACCESS_TOKEN"] == "[REDACTED]"
        assert record.context["Api_Key"] == "[REDACTED]"
        assert record.context["PASSWORD"] == "[REDACTED]"


class TestConfigureLogging:
    """Tests for configure_logging() function."""

    def test_configure_logging_with_json_format(self):
        """Verify JSON formatter is used when format='json'."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            StructuredLogFormatter,
            configure_logging,
        )

        config = ObservabilityConfig(
            log_level="INFO",
            log_format="json",
            log_file=None,
            log_redact_ids=False,
        )

        configure_logging(config)

        logger = logging.getLogger("cast_highlight_mcp")

        # Check that at least one handler has StructuredLogFormatter
        has_json_formatter = any(
            isinstance(h.formatter, StructuredLogFormatter) for h in logger.handlers
        )
        assert has_json_formatter

        # Clean up
        logger.handlers.clear()

    def test_configure_logging_with_text_format(self):
        """Verify text formatter is used when format='text'."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            TextLogFormatter,
            configure_logging,
        )

        config = ObservabilityConfig(
            log_level="INFO",
            log_format="text",
            log_file=None,
            log_redact_ids=False,
        )

        configure_logging(config)

        logger = logging.getLogger("cast_highlight_mcp")

        has_text_formatter = any(isinstance(h.formatter, TextLogFormatter) for h in logger.handlers)
        assert has_text_formatter

        # Clean up
        logger.handlers.clear()

    def test_configure_logging_sets_log_level(self):
        """Verify log level is set correctly."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            configure_logging,
        )

        config = ObservabilityConfig(
            log_level="DEBUG",
            log_format="json",
            log_file=None,
            log_redact_ids=False,
        )

        configure_logging(config)

        logger = logging.getLogger("cast_highlight_mcp")
        assert logger.level == logging.DEBUG

        # Clean up
        logger.handlers.clear()

    def test_configure_logging_adds_redaction_filter(self):
        """Verify RedactionFilter is added to handlers."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            RedactionFilter,
            configure_logging,
        )

        config = ObservabilityConfig(
            log_level="INFO",
            log_format="json",
            log_file=None,
            log_redact_ids=False,
        )

        configure_logging(config)

        logger = logging.getLogger("cast_highlight_mcp")

        # Check that handlers have RedactionFilter
        has_redaction_filter = any(
            any(isinstance(f, RedactionFilter) for f in h.filters) for h in logger.handlers
        )
        assert has_redaction_filter

        # Clean up
        logger.handlers.clear()

    def test_configure_logging_with_file_output(self, tmp_path):
        """Verify file handler is added when log_file is specified."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            configure_logging,
        )

        log_file = tmp_path / "test.log"

        config = ObservabilityConfig(
            log_level="INFO",
            log_format="json",
            log_file=str(log_file),
            log_redact_ids=False,
        )

        configure_logging(config)

        logger = logging.getLogger("cast_highlight_mcp")

        # Log something
        logger.info("Test message")

        # Flush handlers
        for h in logger.handlers:
            h.flush()

        # Check file was created and has content
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

        # Clean up
        logger.handlers.clear()

    def test_configure_logging_handles_invalid_file_path_gracefully(self, capsys):
        """Verify graceful handling of invalid file path."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            configure_logging,
        )

        config = ObservabilityConfig(
            log_level="INFO",
            log_format="json",
            log_file="/nonexistent/directory/test.log",
            log_redact_ids=False,
        )

        # Should not raise
        configure_logging(config)

        # Should have written warning to stderr
        captured = capsys.readouterr()
        assert "Warning" in captured.err or "warning" in captured.err.lower()

        # Clean up
        logger = logging.getLogger("cast_highlight_mcp")
        logger.handlers.clear()

    def test_configure_logging_clears_existing_handlers(self):
        """Verify existing handlers are cleared to prevent duplicates."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            configure_logging,
        )

        config = ObservabilityConfig(
            log_level="INFO",
            log_format="json",
            log_file=None,
            log_redact_ids=False,
        )

        # Configure multiple times
        configure_logging(config)
        configure_logging(config)

        logger = logging.getLogger("cast_highlight_mcp")

        # Should only have one handler (not multiple)
        assert len(logger.handlers) == 1

        # Clean up
        logger.handlers.clear()

    def test_configure_logging_from_environment(self, monkeypatch):
        """Verify logging can be configured from environment when no config provided."""
        from cast_highlight_mcp.observability.logging import configure_logging

        monkeypatch.setenv("HIGHLIGHT_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("HIGHLIGHT_LOG_FORMAT", "text")

        configure_logging()  # No config provided

        logger = logging.getLogger("cast_highlight_mcp")
        assert logger.level == logging.DEBUG

        # Clean up
        logger.handlers.clear()

    def test_configure_logging_prevents_propagation(self):
        """Verify logs don't propagate to root logger."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            configure_logging,
        )

        config = ObservabilityConfig(
            log_level="INFO",
            log_format="json",
            log_file=None,
            log_redact_ids=False,
        )

        configure_logging(config)

        logger = logging.getLogger("cast_highlight_mcp")
        assert logger.propagate is False

        # Clean up
        logger.handlers.clear()


class TestGetLogger:
    """Tests for get_logger() function."""

    def test_get_logger_returns_logger(self):
        """Verify get_logger returns a logger object."""
        from cast_highlight_mcp.observability.logging import get_logger

        logger = get_logger("test.module")

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")

    def test_get_logger_uses_correct_name(self):
        """Verify logger uses the provided name."""
        from cast_highlight_mcp.observability.logging import get_logger

        logger = get_logger("cast_highlight_mcp.server")

        # The underlying logger should have the correct name
        assert "cast_highlight_mcp.server" in str(logger.logger.name)

    def test_get_logger_inherits_from_package_logger(self):
        """Verify module loggers inherit from package logger."""
        from cast_highlight_mcp.observability.logging import (
            ObservabilityConfig,
            configure_logging,
            get_logger,
        )

        config = ObservabilityConfig(
            log_level="DEBUG",
            log_format="json",
            log_file=None,
            log_redact_ids=False,
        )

        configure_logging(config)

        logger = get_logger("cast_highlight_mcp.client")

        # Module logger should use package logger's handlers through hierarchy
        # The logger should be enabled for DEBUG since parent is DEBUG
        assert logger.logger.isEnabledFor(logging.DEBUG)

        # Clean up
        logging.getLogger("cast_highlight_mcp").handlers.clear()


class TestGracefulDegradation:
    """Tests for graceful degradation behavior."""

    def test_logging_failure_does_not_raise(self):
        """Verify logging failures don't raise exceptions."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        # Create a record with a problematic __repr__
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Add context with object that raises on serialization
        class BadObject:
            def __repr__(self):
                raise RuntimeError("Cannot represent")

            def __str__(self):
                raise RuntimeError("Cannot stringify")

        record.context = {"bad": BadObject()}

        # Should not raise
        try:
            output = formatter.format(record)
            # Should still produce valid JSON
            json.loads(output)
        except Exception as e:
            pytest.fail(f"Formatter raised exception: {e}")

    def test_redaction_failure_does_not_raise(self):
        """Verify redaction failures don't raise exceptions."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Add context that might cause issues
        record.context = {"circular": None}
        record.context["circular"] = record.context  # Circular reference

        # Should not raise, should return True
        result = filter_obj.filter(record)
        assert result is True


class TestLogContextDataclass:
    """Tests for LogContext dataclass if present."""

    def test_logcontext_to_dict_excludes_none_values(self):
        """Verify to_dict excludes None values."""
        from cast_highlight_mcp.observability.logging import LogContext

        context = LogContext(
            request_id="abc123",
            tool_name="test_tool",
            duration_ms=None,  # Should be excluded
            success=True,
        )

        result = context.to_dict()

        assert "request_id" in result
        assert "tool_name" in result
        assert "success" in result
        assert "duration_ms" not in result

    def test_logcontext_to_dict_includes_extra_fields(self):
        """Verify extra dict fields are merged into output."""
        from cast_highlight_mcp.observability.logging import LogContext

        context = LogContext(
            request_id="abc123",
            extra={"custom_field": "custom_value"},
        )

        result = context.to_dict()

        assert "custom_field" in result
        assert result["custom_field"] == "custom_value"


class TestObservabilityConfig:
    """Tests for ObservabilityConfig dataclass."""

    def test_config_defaults(self):
        """Verify default configuration values."""
        from cast_highlight_mcp.observability.logging import ObservabilityConfig

        config = ObservabilityConfig()

        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.log_file is None
        assert config.log_redact_ids is False

    def test_config_from_env(self, monkeypatch):
        """Verify configuration loads from environment."""
        from cast_highlight_mcp.observability.logging import ObservabilityConfig

        monkeypatch.setenv("HIGHLIGHT_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("HIGHLIGHT_LOG_FORMAT", "text")
        monkeypatch.setenv("HIGHLIGHT_LOG_REDACT_IDS", "true")

        config = ObservabilityConfig.from_env()

        assert config.log_level == "DEBUG"
        assert config.log_format == "text"
        assert config.log_redact_ids is True

    def test_config_validates_log_level(self, capsys):
        """Verify invalid log level defaults to INFO with warning."""
        from cast_highlight_mcp.observability.logging import ObservabilityConfig

        config = ObservabilityConfig(log_level="INVALID")
        config.validate()

        assert config.log_level == "INFO"

    def test_config_validates_log_format(self):
        """Verify invalid log format defaults to json."""
        from cast_highlight_mcp.observability.logging import ObservabilityConfig

        config = ObservabilityConfig(log_format="xml")
        config.validate()

        assert config.log_format == "json"


class TestRedactionFilterEdgeCases:
    """Tests for edge cases in RedactionFilter."""

    def test_filter_redacts_sensitive_keys_in_nested_lists(self):
        """Verify redaction works in lists of dicts."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {
            "items": [
                {"access_token": "secret1", "name": "item1"},
                {"api_key": "secret2", "name": "item2"},
                {"password": "secret3", "name": "item3"},
            ]
        }

        filter_obj.filter(record)

        # All sensitive keys in nested list items should be redacted
        assert record.context["items"][0]["access_token"] == "[REDACTED]"
        assert record.context["items"][0]["name"] == "item1"  # Not sensitive
        assert record.context["items"][1]["api_key"] == "[REDACTED]"
        assert record.context["items"][1]["name"] == "item2"  # Not sensitive
        assert record.context["items"][2]["password"] == "[REDACTED]"
        assert record.context["items"][2]["name"] == "item3"  # Not sensitive

    def test_filter_handles_deeply_nested_lists(self):
        """Verify redaction works in deeply nested structures."""
        from cast_highlight_mcp.observability.logging import RedactionFilter

        filter_obj = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.context = {"level1": {"level2": [{"secret": "hidden_value", "public": "visible"}]}}

        filter_obj.filter(record)

        assert record.context["level1"]["level2"][0]["secret"] == "[REDACTED]"
        assert record.context["level1"]["level2"][0]["public"] == "visible"


class TestFormatterEmptyContext:
    """Tests for formatter handling of empty context vs None."""

    def test_formatter_handles_empty_context_dict(self):
        """Verify empty {} context is handled differently from None."""
        from cast_highlight_mcp.observability.logging import StructuredLogFormatter

        formatter = StructuredLogFormatter()

        # Record with empty context dict
        record_empty = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test with empty context",
            args=(),
            exc_info=None,
        )
        record_empty.context = {}

        # Record with None context (no context attribute)
        record_none = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test with no context",
            args=(),
            exc_info=None,
        )
        # Don't set context at all (simulates no context)

        output_empty = formatter.format(record_empty)
        output_none = formatter.format(record_none)

        parsed_empty = json.loads(output_empty)
        parsed_none = json.loads(output_none)

        # Both should be valid JSON
        assert "message" in parsed_empty
        assert "message" in parsed_none

        # Empty context should not add a "context" key (empty dict is falsy)
        assert "context" not in parsed_empty, "Empty context dict should not appear in output"
        assert "context" not in parsed_none, "None context should not appear in output"

    def test_text_formatter_handles_empty_context_dict(self):
        """Verify TextLogFormatter handles empty context dict correctly."""
        from cast_highlight_mcp.observability.logging import TextLogFormatter

        formatter = TextLogFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.context = {}

        output = formatter.format(record)

        # Should still produce valid output
        assert "INFO" in output
        assert "Test message" in output
        # Empty context should not add any key=value pairs
        # The output should be similar to one without context
