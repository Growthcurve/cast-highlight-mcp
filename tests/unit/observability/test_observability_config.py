"""Tests for observability configuration module."""

import pytest

from cast_highlight_mcp.config import (
    ObservabilityConfig,
    _parse_bool,
    _validate_log_format,
    _validate_log_level,
    load_observability_config,
)


class TestObservabilityConfig:
    """Tests for ObservabilityConfig dataclass."""

    def test_observability_config_creation_with_defaults(self):
        """Test creating ObservabilityConfig with default values."""
        config = ObservabilityConfig()
        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.log_file is None
        assert config.log_redact_ids is False
        assert config.metrics_enabled is True
        assert config.metrics_prefix == "highlight"
        assert config.metrics_detailed is False

    def test_observability_config_creation_with_custom_values(self):
        """Test creating ObservabilityConfig with custom values."""
        config = ObservabilityConfig(
            log_level="DEBUG",
            log_format="text",
            log_file="/var/log/mcp.log",
            log_redact_ids=True,
            metrics_enabled=False,
            metrics_prefix="custom",
            metrics_detailed=True,
        )
        assert config.log_level == "DEBUG"
        assert config.log_format == "text"
        assert config.log_file == "/var/log/mcp.log"
        assert config.log_redact_ids is True
        assert config.metrics_enabled is False
        assert config.metrics_prefix == "custom"
        assert config.metrics_detailed is True


class TestParseBool:
    """Tests for _parse_bool helper function."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("Yes", True),
            ("YES", True),
            ("on", True),
            ("On", True),
            ("ON", True),
        ],
    )
    def test_parse_bool_true_values(self, value: str, expected: bool):
        """Test that true-like values are parsed correctly."""
        assert _parse_bool(value) is expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("No", False),
            ("NO", False),
            ("off", False),
            ("Off", False),
            ("OFF", False),
            ("", False),
            ("invalid", False),
            ("random", False),
        ],
    )
    def test_parse_bool_false_values(self, value: str, expected: bool):
        """Test that false-like values are parsed correctly."""
        assert _parse_bool(value) is expected

    def test_parse_bool_none(self):
        """Test that None is parsed as False."""
        assert _parse_bool(None) is False


class TestValidateLogLevel:
    """Tests for _validate_log_level helper function."""

    @pytest.mark.parametrize(
        "level,expected",
        [
            ("DEBUG", "DEBUG"),
            ("INFO", "INFO"),
            ("WARNING", "WARNING"),
            ("ERROR", "ERROR"),
            ("CRITICAL", "CRITICAL"),
        ],
    )
    def test_validate_log_level_valid_uppercase(self, level: str, expected: str):
        """Test valid uppercase log levels pass through."""
        assert _validate_log_level(level) == expected

    @pytest.mark.parametrize(
        "level,expected",
        [
            ("debug", "DEBUG"),
            ("info", "INFO"),
            ("warning", "WARNING"),
            ("error", "ERROR"),
            ("critical", "CRITICAL"),
        ],
    )
    def test_validate_log_level_case_insensitive(self, level: str, expected: str):
        """Test log levels are case-insensitive."""
        assert _validate_log_level(level) == expected

    @pytest.mark.parametrize(
        "level,expected",
        [
            ("Debug", "DEBUG"),
            ("Info", "INFO"),
            ("Warning", "WARNING"),
            ("Error", "ERROR"),
            ("Critical", "CRITICAL"),
        ],
    )
    def test_validate_log_level_mixed_case(self, level: str, expected: str):
        """Test mixed case log levels are normalized."""
        assert _validate_log_level(level) == expected

    def test_validate_log_level_warn_alias(self):
        """Test WARN is aliased to WARNING."""
        assert _validate_log_level("WARN") == "WARNING"
        assert _validate_log_level("warn") == "WARNING"
        assert _validate_log_level("Warn") == "WARNING"

    def test_validate_log_level_invalid_defaults_to_info(self, capsys):
        """Test invalid log level defaults to INFO with warning."""
        result = _validate_log_level("invalid")
        assert result == "INFO"
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "invalid" in captured.err.lower()

    def test_validate_log_level_empty_defaults_to_info(self, capsys):
        """Test empty string defaults to INFO with warning."""
        result = _validate_log_level("")
        assert result == "INFO"
        captured = capsys.readouterr()
        assert "WARNING" in captured.err


class TestValidateLogFormat:
    """Tests for _validate_log_format helper function."""

    def test_validate_log_format_json(self):
        """Test json format passes through."""
        assert _validate_log_format("json") == "json"
        assert _validate_log_format("JSON") == "json"
        assert _validate_log_format("Json") == "json"

    def test_validate_log_format_text(self):
        """Test text format passes through."""
        assert _validate_log_format("text") == "text"
        assert _validate_log_format("TEXT") == "text"
        assert _validate_log_format("Text") == "text"

    def test_validate_log_format_invalid_defaults_to_json(self, capsys):
        """Test invalid format defaults to json with warning."""
        result = _validate_log_format("invalid")
        assert result == "json"
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "invalid" in captured.err.lower()


class TestLoadObservabilityConfig:
    """Tests for load_observability_config function."""

    def test_load_observability_config_defaults(self, monkeypatch):
        """Test loading config returns defaults when no env vars set."""
        # Clear all observability env vars
        monkeypatch.delenv("HIGHLIGHT_LOG_LEVEL", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_FORMAT", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_FILE", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_REDACT_IDS", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_ENABLED", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_PREFIX", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_DETAILED", raising=False)

        config = load_observability_config()

        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.log_file is None
        assert config.log_redact_ids is False
        assert config.metrics_enabled is True
        assert config.metrics_prefix == "highlight"
        assert config.metrics_detailed is False

    def test_load_observability_config_custom_values(self, monkeypatch):
        """Test loading config with all custom values."""
        monkeypatch.setenv("HIGHLIGHT_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("HIGHLIGHT_LOG_FORMAT", "text")
        monkeypatch.setenv("HIGHLIGHT_LOG_FILE", "/tmp/test.log")
        monkeypatch.setenv("HIGHLIGHT_LOG_REDACT_IDS", "true")
        monkeypatch.setenv("HIGHLIGHT_METRICS_ENABLED", "false")
        monkeypatch.setenv("HIGHLIGHT_METRICS_PREFIX", "custom")
        monkeypatch.setenv("HIGHLIGHT_METRICS_DETAILED", "true")

        config = load_observability_config()

        assert config.log_level == "DEBUG"
        assert config.log_format == "text"
        assert config.log_file == "/tmp/test.log"
        assert config.log_redact_ids is True
        assert config.metrics_enabled is False
        assert config.metrics_prefix == "custom"
        assert config.metrics_detailed is True

    def test_load_observability_config_log_level_validation(self, monkeypatch, capsys):
        """Test invalid log level is handled gracefully."""
        monkeypatch.setenv("HIGHLIGHT_LOG_LEVEL", "INVALID")
        monkeypatch.delenv("HIGHLIGHT_LOG_FORMAT", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_FILE", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_REDACT_IDS", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_ENABLED", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_PREFIX", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_DETAILED", raising=False)

        config = load_observability_config()

        assert config.log_level == "INFO"  # Defaults to INFO
        captured = capsys.readouterr()
        assert "WARNING" in captured.err

    def test_load_observability_config_log_format_validation(self, monkeypatch, capsys):
        """Test invalid log format is handled gracefully."""
        monkeypatch.setenv("HIGHLIGHT_LOG_FORMAT", "xml")
        monkeypatch.delenv("HIGHLIGHT_LOG_LEVEL", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_FILE", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_REDACT_IDS", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_ENABLED", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_PREFIX", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_DETAILED", raising=False)

        config = load_observability_config()

        assert config.log_format == "json"  # Defaults to json
        captured = capsys.readouterr()
        assert "WARNING" in captured.err

    def test_load_observability_config_empty_log_file(self, monkeypatch):
        """Test empty log file is converted to None."""
        monkeypatch.setenv("HIGHLIGHT_LOG_FILE", "")
        monkeypatch.delenv("HIGHLIGHT_LOG_LEVEL", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_FORMAT", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_REDACT_IDS", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_ENABLED", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_PREFIX", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_DETAILED", raising=False)

        config = load_observability_config()

        assert config.log_file is None

    @pytest.mark.parametrize(
        "level",
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    def test_load_observability_config_all_valid_log_levels(self, monkeypatch, level: str):
        """Test all valid log levels are accepted."""
        monkeypatch.setenv("HIGHLIGHT_LOG_LEVEL", level)
        monkeypatch.delenv("HIGHLIGHT_LOG_FORMAT", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_FILE", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_REDACT_IDS", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_ENABLED", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_PREFIX", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_DETAILED", raising=False)

        config = load_observability_config()

        assert config.log_level == level

    def test_load_observability_config_metrics_enabled_default_true(self, monkeypatch):
        """Test metrics_enabled defaults to True."""
        monkeypatch.delenv("HIGHLIGHT_LOG_LEVEL", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_FORMAT", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_FILE", raising=False)
        monkeypatch.delenv("HIGHLIGHT_LOG_REDACT_IDS", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_ENABLED", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_PREFIX", raising=False)
        monkeypatch.delenv("HIGHLIGHT_METRICS_DETAILED", raising=False)

        config = load_observability_config()

        assert config.metrics_enabled is True
