"""Tests for HighlightClient retry logic with exponential backoff (Issue #2)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from cast_highlight_mcp.client import HighlightClient, _is_retryable_exception
from cast_highlight_mcp.config import Config


@pytest.fixture
def mock_config():
    """Create a mock config for testing with retry settings."""
    return Config(
        base_url="https://api.casthighlight.com/WS2",
        access_token="test-token-abc123",
        company_id=1234,
        timeout=30,
        retry_attempts=3,
        retry_min_wait=0.01,  # Short waits for testing
        retry_max_wait=0.1,
        retry_multiplier=2.0,
    )


@pytest.fixture
def client(mock_config):
    """Create a HighlightClient instance for testing."""
    return HighlightClient(mock_config)


class TestIsRetryableException:
    """Tests for _is_retryable_exception helper function."""

    def test_connect_error_is_retryable(self):
        """Test that ConnectError triggers retry."""
        exc = httpx.ConnectError("Connection refused")
        assert _is_retryable_exception(exc) is True

    def test_timeout_exception_is_retryable(self):
        """Test that TimeoutException triggers retry."""
        exc = httpx.TimeoutException("Request timed out")
        assert _is_retryable_exception(exc) is True

    def test_429_rate_limit_is_retryable(self):
        """Test that 429 Too Many Requests triggers retry."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        exc = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is True

    def test_500_server_error_is_retryable(self):
        """Test that 500 Internal Server Error triggers retry."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        exc = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is True

    def test_502_bad_gateway_is_retryable(self):
        """Test that 502 Bad Gateway triggers retry."""
        mock_response = MagicMock()
        mock_response.status_code = 502
        exc = httpx.HTTPStatusError(
            "502 Bad Gateway",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is True

    def test_503_service_unavailable_is_retryable(self):
        """Test that 503 Service Unavailable triggers retry."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        exc = httpx.HTTPStatusError(
            "503 Service Unavailable",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is True

    def test_504_gateway_timeout_is_retryable(self):
        """Test that 504 Gateway Timeout triggers retry."""
        mock_response = MagicMock()
        mock_response.status_code = 504
        exc = httpx.HTTPStatusError(
            "504 Gateway Timeout",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is True

    def test_501_not_implemented_is_not_retryable(self):
        """Test that 501 Not Implemented does NOT trigger retry."""
        mock_response = MagicMock()
        mock_response.status_code = 501
        exc = httpx.HTTPStatusError(
            "501 Not Implemented",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is False

    def test_400_bad_request_is_not_retryable(self):
        """Test that 400 Bad Request does NOT trigger retry."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        exc = httpx.HTTPStatusError(
            "400 Bad Request",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is False

    def test_401_unauthorized_is_not_retryable(self):
        """Test that 401 Unauthorized does NOT trigger retry."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        exc = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is False

    def test_403_forbidden_is_not_retryable(self):
        """Test that 403 Forbidden does NOT trigger retry."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        exc = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is False

    def test_404_not_found_is_not_retryable(self):
        """Test that 404 Not Found does NOT trigger retry."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        exc = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )
        assert _is_retryable_exception(exc) is False

    def test_generic_exception_is_not_retryable(self):
        """Test that generic Exception does NOT trigger retry."""
        exc = Exception("Something went wrong")
        assert _is_retryable_exception(exc) is False

    def test_value_error_is_not_retryable(self):
        """Test that ValueError does NOT trigger retry."""
        exc = ValueError("Invalid value")
        assert _is_retryable_exception(exc) is False


class TestRetryOnTransientFailures:
    """Tests for retry behavior on transient failures."""

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self, client):
        """Test that _request retries on connection errors."""
        mock_http_client = AsyncMock()

        # Fail twice, then succeed
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection refused")
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": "success"}
            response.raise_for_status = MagicMock()
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        result = await client._request("GET", "/test")

        assert result == {"data": "success"}
        assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self, client):
        """Test that _request retries on timeout errors."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": "success"}
            response.raise_for_status = MagicMock()
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        result = await client._request("GET", "/test")

        assert result == {"data": "success"}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_503_service_unavailable(self, client):
        """Test that _request retries on 503 errors."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            if call_count < 2:
                response.status_code = 503
                response.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "503 Service Unavailable",
                        request=MagicMock(),
                        response=MagicMock(status_code=503),
                    )
                )
            else:
                response.status_code = 200
                response.json.return_value = {"data": "success"}
                response.raise_for_status = MagicMock()
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        result = await client._request("GET", "/test")

        assert result == {"data": "success"}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_429_rate_limit(self, client):
        """Test that _request retries on 429 rate limit errors."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            if call_count < 2:
                response.status_code = 429
                response.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "429 Too Many Requests",
                        request=MagicMock(),
                        response=MagicMock(status_code=429),
                    )
                )
            else:
                response.status_code = 200
                response.json.return_value = {"data": "success"}
                response.raise_for_status = MagicMock()
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        result = await client._request("GET", "/test")

        assert result == {"data": "success"}
        assert call_count == 2


class TestNoRetryOnClientErrors:
    """Tests that client errors do NOT trigger retries."""

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self, client):
        """Test that 404 errors do NOT trigger retry."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 404
            response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "404 Not Found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                )
            )
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with pytest.raises(httpx.HTTPStatusError):
            await client._request("GET", "/test")

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_no_retry_on_401(self, client):
        """Test that 401 errors do NOT trigger retry."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 401
            response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "401 Unauthorized",
                    request=MagicMock(),
                    response=MagicMock(status_code=401),
                )
            )
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with pytest.raises(httpx.HTTPStatusError):
            await client._request("GET", "/test")

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_no_retry_on_501(self, client):
        """Test that 501 Not Implemented does NOT trigger retry."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 501
            response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "501 Not Implemented",
                    request=MagicMock(),
                    response=MagicMock(status_code=501),
                )
            )
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with pytest.raises(httpx.HTTPStatusError):
            await client._request("GET", "/test")

        assert call_count == 1  # No retries


class TestRetryExhaustion:
    """Tests for behavior when all retries are exhausted."""

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_connection_error(self, client):
        """Test that connection errors are raised after max retries."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with pytest.raises(httpx.ConnectError):
            await client._request("GET", "/test")

        # Should have tried 3 times (retry_attempts=3)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_timeout(self, client):
        """Test that timeout errors are raised after max retries."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Request timed out")

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with pytest.raises(httpx.TimeoutException):
            await client._request("GET", "/test")

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_503(self, client):
        """Test that 503 errors are raised after max retries."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 503
            response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "503 Service Unavailable",
                    request=MagicMock(),
                    response=MagicMock(status_code=503),
                )
            )
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with pytest.raises(httpx.HTTPStatusError):
            await client._request("GET", "/test")

        assert call_count == 3


class TestRetryConfiguration:
    """Tests for retry configuration from Config."""

    @pytest.mark.asyncio
    async def test_respects_custom_retry_attempts(self):
        """Test that retry_attempts config is respected."""
        config = Config(
            base_url="https://api.casthighlight.com/WS2",
            access_token="test-token",
            company_id=1234,
            retry_attempts=5,  # Custom: 5 attempts
            retry_min_wait=0.001,
            retry_max_wait=0.01,
            retry_multiplier=1.0,
        )
        client = HighlightClient(config)

        mock_http_client = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with pytest.raises(httpx.ConnectError):
            await client._request("GET", "/test")

        assert call_count == 5  # Should respect the custom retry_attempts

    @pytest.mark.asyncio
    async def test_single_retry_attempt_means_no_retry(self):
        """Test that retry_attempts=1 means no retries."""
        config = Config(
            base_url="https://api.casthighlight.com/WS2",
            access_token="test-token",
            company_id=1234,
            retry_attempts=1,  # Single attempt = no retries
            retry_min_wait=0.001,
            retry_max_wait=0.01,
            retry_multiplier=1.0,
        )
        client = HighlightClient(config)

        mock_http_client = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with pytest.raises(httpx.ConnectError):
            await client._request("GET", "/test")

        assert call_count == 1  # Only one attempt


class TestRetryLogging:
    """Tests for retry logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_attempt_number_on_retry(self, client):
        """Test that attempt number is included in logs when retrying."""
        mock_http_client = AsyncMock()

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": "success"}
            response.raise_for_status = MagicMock()
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        with patch("cast_highlight_mcp.client.logger") as mock_logger:
            await client._request("GET", "/test")

            # Check that at least one log call includes attempt > 1
            logged_attempts = []
            for call in mock_logger.log.call_args_list:
                if len(call.kwargs.get("extra", {}).get("context", {})) > 0:
                    attempt = call.kwargs["extra"]["context"].get("attempt")
                    if attempt:
                        logged_attempts.append(attempt)

            # The successful request (attempt 2) should be logged with attempt number
            assert 2 in logged_attempts


class TestRetryEdgeCases:
    """Tests for edge cases in retry behavior."""

    def test_read_timeout_is_retryable(self):
        """Test that ReadTimeout (subclass of TimeoutException) triggers retry."""
        exc = httpx.ReadTimeout("Read timed out")
        assert _is_retryable_exception(exc) is True

    def test_write_timeout_is_retryable(self):
        """Test that WriteTimeout (subclass of TimeoutException) triggers retry."""
        exc = httpx.WriteTimeout("Write timed out")
        assert _is_retryable_exception(exc) is True

    def test_connect_timeout_is_retryable(self):
        """Test that ConnectTimeout (subclass of TimeoutException) triggers retry."""
        exc = httpx.ConnectTimeout("Connect timed out")
        assert _is_retryable_exception(exc) is True

    @pytest.mark.asyncio
    async def test_retries_on_500_then_succeeds(self):
        """Test that _request retries on 500 and succeeds on next attempt."""
        config = Config(
            base_url="https://api.casthighlight.com/WS2",
            access_token="test-token",
            company_id=1234,
            retry_attempts=3,
            retry_min_wait=0.001,
            retry_max_wait=0.01,
            retry_multiplier=1.0,
        )
        client = HighlightClient(config)

        mock_http_client = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            if call_count == 1:
                response.status_code = 500
                response.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "500 Internal Server Error",
                        request=MagicMock(),
                        response=MagicMock(status_code=500),
                    )
                )
            else:
                response.status_code = 200
                response.json.return_value = {"recovered": True}
                response.raise_for_status = MagicMock()
            return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        result = await client._request("GET", "/test")

        assert result == {"recovered": True}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_mixed_errors_during_retries(self):
        """Test handling of different error types during retry sequence."""
        config = Config(
            base_url="https://api.casthighlight.com/WS2",
            access_token="test-token",
            company_id=1234,
            retry_attempts=4,
            retry_min_wait=0.001,
            retry_max_wait=0.01,
            retry_multiplier=1.0,
        )
        client = HighlightClient(config)

        mock_http_client = AsyncMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("Connection refused")
            elif call_count == 2:
                raise httpx.TimeoutException("Timeout")
            elif call_count == 3:
                response = MagicMock()
                response.status_code = 503
                response.raise_for_status = MagicMock(
                    side_effect=httpx.HTTPStatusError(
                        "503 Service Unavailable",
                        request=MagicMock(),
                        response=MagicMock(status_code=503),
                    )
                )
                return response
            else:
                response = MagicMock()
                response.status_code = 200
                response.json.return_value = {"finally": "success"}
                response.raise_for_status = MagicMock()
                return response

        mock_http_client.request = AsyncMock(side_effect=side_effect)
        client._client = mock_http_client

        result = await client._request("GET", "/test")

        assert result == {"finally": "success"}
        assert call_count == 4


class TestConfigDefaults:
    """Tests for Config default values for retry settings."""

    def test_config_has_default_retry_attempts(self):
        """Test Config has default retry_attempts=3."""
        config = Config(
            base_url="https://example.com",
            access_token="token",
            company_id=1,
        )
        assert config.retry_attempts == 3

    def test_config_has_default_retry_min_wait(self):
        """Test Config has default retry_min_wait=1.0."""
        config = Config(
            base_url="https://example.com",
            access_token="token",
            company_id=1,
        )
        assert config.retry_min_wait == 1.0

    def test_config_has_default_retry_max_wait(self):
        """Test Config has default retry_max_wait=10.0."""
        config = Config(
            base_url="https://example.com",
            access_token="token",
            company_id=1,
        )
        assert config.retry_max_wait == 10.0

    def test_config_has_default_retry_multiplier(self):
        """Test Config has default retry_multiplier=2.0."""
        config = Config(
            base_url="https://example.com",
            access_token="token",
            company_id=1,
        )
        assert config.retry_multiplier == 2.0
