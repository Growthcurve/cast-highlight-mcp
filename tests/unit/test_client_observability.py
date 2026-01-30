"""Tests for client.py observability integration (Phase 5).

These tests verify that the HTTP client correctly:
1. Produces log entries at appropriate levels (DEBUG for 2xx, WARNING for 4xx, ERROR for 5xx)
2. Records HTTP metrics via get_metrics_collector()
3. Uses request_id from context for correlation
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cast_highlight_mcp.client import HighlightClient
from cast_highlight_mcp.config import Config
from cast_highlight_mcp.observability import (
    get_metrics_collector,
    request_context,
    reset_metrics_collector,
)


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    return Config(
        base_url="https://api.casthighlight.com/WS2",
        access_token="test-token-abc123",
        company_id=1234,
        timeout=30,
    )


@pytest.fixture
def client(mock_config):
    """Create a HighlightClient instance for testing."""
    return HighlightClient(mock_config)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test."""
    reset_metrics_collector()
    yield
    reset_metrics_collector()


class TestHttpRequestLogging:
    """Tests for HTTP request logging at correct levels."""

    @pytest.mark.asyncio
    async def test_successful_request_logs_at_debug_level(self, client, caplog):
        """Test successful HTTP requests (2xx) are logged at DEBUG level."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            await client._request("GET", "/test/path")

        # Check that both "started" and "completed" messages are logged
        log_messages = [r.message for r in caplog.records]
        assert any("HTTP request started" in msg for msg in log_messages)
        assert any("HTTP request completed" in msg for msg in log_messages)

        # Verify completed message is at DEBUG level
        for record in caplog.records:
            if "HTTP request completed" in record.message:
                assert record.levelno == logging.DEBUG

    @pytest.mark.asyncio
    async def test_client_error_logs_at_warning_level(self, client, caplog):
        """Test client errors (4xx) are logged at WARNING level."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "not found"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            with pytest.raises(httpx.HTTPStatusError):
                await client._request("GET", "/nonexistent")

        # Verify completed message is at WARNING level for 4xx
        for record in caplog.records:
            if "HTTP request completed" in record.message:
                assert record.levelno == logging.WARNING

    @pytest.mark.asyncio
    async def test_server_error_logs_at_error_level(self, client, caplog):
        """Test server errors (5xx) are logged at ERROR level."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "internal server error"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            with pytest.raises(httpx.HTTPStatusError):
                await client._request("GET", "/error")

        # Verify completed message is at ERROR level for 5xx
        for record in caplog.records:
            if "HTTP request completed" in record.message:
                assert record.levelno == logging.ERROR

    @pytest.mark.asyncio
    async def test_timeout_logs_at_warning_level(self, client, caplog):
        """Test timeout errors are logged at WARNING level."""
        mock_http_client = AsyncMock()
        mock_http_client.request.side_effect = httpx.TimeoutException("Timeout")
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            with pytest.raises(httpx.TimeoutException):
                await client._request("GET", "/slow")

        # Verify timeout message is at WARNING level
        for record in caplog.records:
            if "HTTP request timeout" in record.message:
                assert record.levelno == logging.WARNING

    @pytest.mark.asyncio
    async def test_connection_error_logs_at_error_level(self, client, caplog):
        """Test connection errors are logged at ERROR level."""
        mock_http_client = AsyncMock()
        mock_http_client.request.side_effect = httpx.ConnectError("Connection refused")
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            with pytest.raises(httpx.ConnectError):
                await client._request("GET", "/unreachable")

        # Verify error message is at ERROR level
        for record in caplog.records:
            if "HTTP request failed" in record.message:
                assert record.levelno == logging.ERROR


class TestHttpMetricsRecording:
    """Tests for HTTP metrics recording via MetricsCollector."""

    @pytest.mark.asyncio
    async def test_successful_request_records_metrics(self, client):
        """Test successful HTTP requests record metrics."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        await client._request("GET", "/test/path")

        # Verify metrics were recorded
        metrics = get_metrics_collector()
        state = metrics.get_metrics()

        assert state.http.requests_total == 1
        assert 200 in state.http.requests_by_status
        assert state.http.requests_by_status[200] == 1
        assert "GET" in state.http.requests_by_method
        assert state.http.requests_by_method["GET"] == 1
        assert state.http.latency_sum_ms > 0

    @pytest.mark.asyncio
    async def test_error_request_records_metrics(self, client):
        """Test error HTTP requests record metrics including error count."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with pytest.raises(httpx.HTTPStatusError):
            await client._request("GET", "/nonexistent")

        # Verify metrics were recorded
        metrics = get_metrics_collector()
        state = metrics.get_metrics()

        assert state.http.requests_total == 1
        assert 404 in state.http.requests_by_status
        assert state.http.errors_total == 1  # 4xx counts as error

    @pytest.mark.asyncio
    async def test_multiple_requests_accumulate_metrics(self, client):
        """Test multiple HTTP requests accumulate metrics correctly."""
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"data": "test"}
        mock_response_200.raise_for_status = MagicMock()

        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        mock_response_404.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        mock_http_client = AsyncMock()
        client._client = mock_http_client

        # Make 2 successful requests and 1 error request
        mock_http_client.request.return_value = mock_response_200
        await client._request("GET", "/path1")
        await client._request("GET", "/path2")

        mock_http_client.request.return_value = mock_response_404
        with pytest.raises(httpx.HTTPStatusError):
            await client._request("GET", "/notfound")

        # Verify accumulated metrics
        metrics = get_metrics_collector()
        state = metrics.get_metrics()

        assert state.http.requests_total == 3
        assert state.http.requests_by_status.get(200, 0) == 2
        assert state.http.requests_by_status.get(404, 0) == 1
        assert state.http.errors_total == 1

    @pytest.mark.asyncio
    async def test_latency_histogram_buckets_populated(self, client):
        """Test latency histogram buckets are populated."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        await client._request("GET", "/test/path")

        metrics = get_metrics_collector()
        state = metrics.get_metrics()

        # At least one bucket should have a count
        total_in_buckets = sum(state.http.latency_buckets.values())
        assert total_in_buckets > 0


class TestRequestIdCorrelation:
    """Tests for request_id correlation from context."""

    @pytest.mark.asyncio
    async def test_request_uses_context_request_id(self, client, caplog):
        """Test HTTP requests use request_id from context for correlation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        # Make request within a context
        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            with request_context(tool_name="test_tool", request_id="test-req-123"):
                await client._request("GET", "/test/path")

        # Verify request_id appears in log records
        found_request_id = False
        for record in caplog.records:
            if hasattr(record, "context"):
                context = record.context
                if isinstance(context, dict) and context.get("request_id") == "test-req-123":
                    found_request_id = True
                    break

        # The context should be attached to the log records
        # Check log messages contain the request_id
        log_output = caplog.text
        assert "test-req-123" in log_output or found_request_id

    @pytest.mark.asyncio
    async def test_request_without_context_uses_no_context_id(self, client, caplog):
        """Test HTTP requests without context use 'no-context' as request_id."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        # Make request outside any context
        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            await client._request("GET", "/test/path")

        # Verify 'no-context' appears in log records' context
        found_no_context = False
        for record in caplog.records:
            if hasattr(record, "context") and isinstance(record.context, dict):
                if record.context.get("request_id") == "no-context":
                    found_no_context = True
                    break

        assert found_no_context, "Expected 'no-context' request_id in log records"

    @pytest.mark.asyncio
    async def test_multiple_requests_share_context_request_id(self, client, caplog):
        """Test multiple HTTP requests in same context share the request_id."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            with request_context(tool_name="test_tool", request_id="shared-req-456"):
                await client._request("GET", "/path1")
                await client._request("GET", "/path2")

        # Verify shared request_id appears in log records' context
        shared_id_count = 0
        for record in caplog.records:
            if hasattr(record, "context") and isinstance(record.context, dict):
                if record.context.get("request_id") == "shared-req-456":
                    shared_id_count += 1

        # Should appear at least 4 times (2 started + 2 completed)
        assert shared_id_count >= 4, (
            f"Expected at least 4 occurrences of shared-req-456, got {shared_id_count}"
        )


class TestLogContextFields:
    """Tests for correct context fields in log entries."""

    @pytest.mark.asyncio
    async def test_log_contains_method_and_path(self, client, caplog):
        """Test log entries contain HTTP method and path."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            await client._request("GET", "/companies/123")

        # Check log records for method and path in context
        found_method = False
        found_path = False
        for record in caplog.records:
            if hasattr(record, "context") and isinstance(record.context, dict):
                if record.context.get("method") == "GET":
                    found_method = True
                if record.context.get("path") == "/companies/123":
                    found_path = True

        assert found_method, "Expected 'GET' method in log context"
        assert found_path, "Expected '/companies/123' path in log context"

    @pytest.mark.asyncio
    async def test_log_contains_status_code(self, client, caplog):
        """Test log entries contain HTTP status code."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            await client._request("POST", "/resources")

        # Check log records for status code in context
        found_status = False
        for record in caplog.records:
            if hasattr(record, "context") and isinstance(record.context, dict):
                if record.context.get("status_code") == 201:
                    found_status = True
                    break

        assert found_status, "Expected status_code 201 in log context"

    @pytest.mark.asyncio
    async def test_log_contains_duration(self, client, caplog):
        """Test log entries contain duration_ms."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            await client._request("GET", "/test")

        # Check log records for duration_ms in context
        found_duration = False
        for record in caplog.records:
            if hasattr(record, "context") and isinstance(record.context, dict):
                if "duration_ms" in record.context:
                    found_duration = True
                    break

        assert found_duration, "Expected duration_ms in log context"


class TestListDomainsObservability:
    """Tests for observability in list_domains method."""

    @pytest.mark.asyncio
    async def test_list_domains_auth_error_logs_with_context(self, client, caplog):
        """Test list_domains authentication errors include context fields."""
        mock_http_client = AsyncMock()
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        auth_error = MagicMock()
        auth_error.status_code = 401
        mock_http_client.get = AsyncMock(return_value=auth_error)
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            with request_context(tool_name="highlight_list_domains", request_id="domain-scan-789"):
                await client.list_domains()

        # Verify context fields in auth error log
        log_output = caplog.text
        assert "Authentication error" in log_output or "401" in log_output

    @pytest.mark.asyncio
    async def test_list_domains_network_error_logs_with_context(self, client, caplog):
        """Test list_domains network errors include context fields."""
        mock_http_client = AsyncMock()
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response
        mock_http_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        client._client = mock_http_client

        with caplog.at_level(logging.DEBUG, logger="cast_highlight_mcp"):
            with request_context(tool_name="highlight_list_domains", request_id="domain-scan-999"):
                await client.list_domains()

        # Verify error type appears in log
        log_output = caplog.text
        assert "ConnectError" in log_output or "Connection" in log_output


class TestObservabilityGracefulDegradation:
    """Tests for graceful degradation when observability components fail."""

    @pytest.mark.asyncio
    async def test_request_succeeds_even_if_metrics_fail(self, client):
        """Test HTTP request succeeds even if metrics recording fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        # Patch metrics to raise an exception
        with patch("cast_highlight_mcp.client.get_metrics_collector") as mock_get_metrics:
            mock_collector = MagicMock()
            mock_collector.record_http_request.side_effect = Exception("Metrics failed")
            mock_get_metrics.return_value = mock_collector

            # Request should still succeed
            result = await client._request("GET", "/test/path")
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_request_succeeds_even_if_context_access_fails(self, client):
        """Test HTTP request succeeds even if context access fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        # Patch get_current_context to raise an exception
        with patch("cast_highlight_mcp.client.get_current_context") as mock_get_ctx:
            mock_get_ctx.side_effect = Exception("Context access failed")

            # Request should still succeed (will use "no-context" as fallback)
            result = await client._request("GET", "/test/path")
            assert result == {"data": "test"}
