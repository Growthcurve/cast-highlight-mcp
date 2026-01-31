"""Tests for configuration module."""

from unittest.mock import patch

import pytest

from cast_highlight_mcp.config import Config, load_config


class TestConfig:
    """Tests for Config dataclass."""

    def test_config_creation(self):
        """Test creating a Config with all fields."""
        config = Config(
            base_url="https://example.com/api",
            access_token="token123",
            company_id=999,
            timeout=60,
        )
        assert config.base_url == "https://example.com/api"
        assert config.access_token == "token123"
        assert config.company_id == 999
        assert config.timeout == 60

    def test_config_default_timeout(self):
        """Test Config uses default timeout."""
        config = Config(
            base_url="https://example.com/api",
            access_token="token123",
            company_id=999,
        )
        assert config.timeout == 30


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_success(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.setenv("HIGHLIGHT_TIMEOUT", "45")

        config = load_config()

        assert config.base_url == "https://test.casthighlight.com/WS2"
        assert config.access_token == "test-token"
        assert config.company_id == 1234
        assert config.timeout == 45

    def test_load_config_default_timeout(self, monkeypatch):
        """Test loading config uses default timeout when not specified."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.delenv("HIGHLIGHT_TIMEOUT", raising=False)

        config = load_config()

        assert config.timeout == 30

    @patch("cast_highlight_mcp.config.load_dotenv")
    def test_load_config_missing_base_url(self, mock_dotenv, monkeypatch):
        """Test error when HIGHLIGHT_BASE_URL is missing."""
        monkeypatch.delenv("HIGHLIGHT_BASE_URL", raising=False)
        monkeypatch.delenv("HIGHLIGHT_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HIGHLIGHT_COMPANY_ID", raising=False)
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")

        with pytest.raises(ValueError, match="HIGHLIGHT_BASE_URL"):
            load_config()

    @patch("cast_highlight_mcp.config.load_dotenv")
    def test_load_config_missing_access_token(self, mock_dotenv, monkeypatch):
        """Test error when HIGHLIGHT_ACCESS_TOKEN is missing."""
        monkeypatch.delenv("HIGHLIGHT_BASE_URL", raising=False)
        monkeypatch.delenv("HIGHLIGHT_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HIGHLIGHT_COMPANY_ID", raising=False)
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")

        with pytest.raises(ValueError, match="HIGHLIGHT_ACCESS_TOKEN"):
            load_config()

    @patch("cast_highlight_mcp.config.load_dotenv")
    def test_load_config_missing_company_id(self, mock_dotenv, monkeypatch):
        """Test error when HIGHLIGHT_COMPANY_ID is missing."""
        monkeypatch.delenv("HIGHLIGHT_BASE_URL", raising=False)
        monkeypatch.delenv("HIGHLIGHT_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HIGHLIGHT_COMPANY_ID", raising=False)
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")

        with pytest.raises(ValueError, match="HIGHLIGHT_COMPANY_ID"):
            load_config()


class TestLoadConfigRetrySettings:
    """Tests for retry configuration in load_config (Issue #2)."""

    def test_load_config_default_retry_attempts(self, monkeypatch):
        """Test loading config uses default retry_attempts=3."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.delenv("HIGHLIGHT_RETRY_ATTEMPTS", raising=False)

        config = load_config()

        assert config.retry_attempts == 3

    def test_load_config_custom_retry_attempts(self, monkeypatch):
        """Test loading config with custom retry_attempts."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.setenv("HIGHLIGHT_RETRY_ATTEMPTS", "5")

        config = load_config()

        assert config.retry_attempts == 5

    def test_load_config_default_retry_min_wait(self, monkeypatch):
        """Test loading config uses default retry_min_wait=1.0."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.delenv("HIGHLIGHT_RETRY_MIN_WAIT", raising=False)

        config = load_config()

        assert config.retry_min_wait == 1.0

    def test_load_config_custom_retry_min_wait(self, monkeypatch):
        """Test loading config with custom retry_min_wait."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.setenv("HIGHLIGHT_RETRY_MIN_WAIT", "0.5")

        config = load_config()

        assert config.retry_min_wait == 0.5

    def test_load_config_default_retry_max_wait(self, monkeypatch):
        """Test loading config uses default retry_max_wait=10.0."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.delenv("HIGHLIGHT_RETRY_MAX_WAIT", raising=False)

        config = load_config()

        assert config.retry_max_wait == 10.0

    def test_load_config_custom_retry_max_wait(self, monkeypatch):
        """Test loading config with custom retry_max_wait."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.setenv("HIGHLIGHT_RETRY_MAX_WAIT", "30.0")

        config = load_config()

        assert config.retry_max_wait == 30.0

    def test_load_config_default_retry_multiplier(self, monkeypatch):
        """Test loading config uses default retry_multiplier=2.0."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.delenv("HIGHLIGHT_RETRY_MULTIPLIER", raising=False)

        config = load_config()

        assert config.retry_multiplier == 2.0

    def test_load_config_custom_retry_multiplier(self, monkeypatch):
        """Test loading config with custom retry_multiplier."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.setenv("HIGHLIGHT_RETRY_MULTIPLIER", "1.5")

        config = load_config()

        assert config.retry_multiplier == 1.5

    def test_load_config_all_retry_settings(self, monkeypatch):
        """Test loading config with all custom retry settings."""
        monkeypatch.setenv("HIGHLIGHT_BASE_URL", "https://test.casthighlight.com/WS2")
        monkeypatch.setenv("HIGHLIGHT_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("HIGHLIGHT_COMPANY_ID", "1234")
        monkeypatch.setenv("HIGHLIGHT_RETRY_ATTEMPTS", "5")
        monkeypatch.setenv("HIGHLIGHT_RETRY_MIN_WAIT", "0.5")
        monkeypatch.setenv("HIGHLIGHT_RETRY_MAX_WAIT", "30.0")
        monkeypatch.setenv("HIGHLIGHT_RETRY_MULTIPLIER", "1.5")

        config = load_config()

        assert config.retry_attempts == 5
        assert config.retry_min_wait == 0.5
        assert config.retry_max_wait == 30.0
        assert config.retry_multiplier == 1.5
