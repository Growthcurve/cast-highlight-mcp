"""Tests for HighlightClient HTTP request layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from cast_highlight_mcp.client import HighlightClient
from cast_highlight_mcp.config import Config


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


class TestGetClientMethod:
    """Tests for _get_client lazy initialization."""

    @pytest.mark.asyncio
    async def test_get_client_creates_new_client(self, client):
        """Test _get_client creates a new httpx.AsyncClient."""
        assert client._client is None

        result = await client._get_client()

        assert result is not None
        assert isinstance(result, httpx.AsyncClient)
        assert client._client is result

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_returns_existing_client(self, client):
        """Test _get_client returns existing client on subsequent calls."""
        first = await client._get_client()
        second = await client._get_client()

        assert first is second

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_uses_config_timeout(self, mock_config):
        """Test _get_client uses timeout from config."""
        mock_config.timeout = 60
        client = HighlightClient(mock_config)

        http_client = await client._get_client()

        # Check timeout was set
        assert http_client.timeout.connect == 60.0

        # Clean up
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_sets_auth_headers(self, client):
        """Test _get_client sets authorization headers."""
        http_client = await client._get_client()

        assert http_client.headers["Authorization"] == "Bearer test-token-abc123"
        assert http_client.headers["Accept"] == "application/json"

        # Clean up
        await client.close()


class TestRequestMethod:
    """Tests for _request method."""

    @pytest.mark.asyncio
    async def test_request_makes_http_call(self, client):
        """Test _request makes HTTP request to correct URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response

        client._client = mock_http_client

        result = await client._request("GET", "/test/path")

        mock_http_client.request.assert_called_once_with(
            "GET", "https://api.casthighlight.com/WS2/test/path"
        )
        mock_response.raise_for_status.assert_called_once()
        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_request_passes_kwargs(self, client):
        """Test _request passes additional kwargs to httpx."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response

        client._client = mock_http_client

        await client._request("POST", "/data", json={"key": "value"})

        mock_http_client.request.assert_called_once_with(
            "POST",
            "https://api.casthighlight.com/WS2/data",
            json={"key": "value"},
        )

    @pytest.mark.asyncio
    async def test_request_raises_http_status_error(self, client):
        """Test _request raises HTTPStatusError on bad status."""
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


class TestGetMethod:
    """Tests for get convenience method."""

    @pytest.mark.asyncio
    async def test_get_calls_request_with_get_method(self, client):
        """Test get() calls _request with GET method."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"result": "data"}

            result = await client.get("/companies/1")

            mock_request.assert_called_once_with("GET", "/companies/1")
            assert result == {"result": "data"}

    @pytest.mark.asyncio
    async def test_get_passes_kwargs(self, client):
        """Test get() passes kwargs to _request."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}

            await client.get("/search", params={"q": "test"})

            mock_request.assert_called_once_with("GET", "/search", params={"q": "test"})


class TestListDomainsScanning:
    """Tests for list_domains domain scanning logic."""

    @pytest.mark.asyncio
    async def test_list_domains_scans_for_domains(self, client):
        """Test list_domains scans ID range for accessible domains."""
        mock_http_client = AsyncMock()

        # Company response with 2 domains
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 2}
        company_response.raise_for_status = MagicMock()

        # Domain responses - success for some IDs
        domain_success = MagicMock()
        domain_success.status_code = 200
        domain_success.json.return_value = {"id": 1234, "name": "Domain 1"}

        domain_success_2 = MagicMock()
        domain_success_2.status_code = 200
        domain_success_2.json.return_value = {"id": 1235, "name": "Domain 2"}

        domain_not_found = MagicMock()
        domain_not_found.status_code = 404

        # First request gets company
        mock_http_client.request.return_value = company_response

        # Subsequent get calls return different responses based on ID
        def mock_get(url):
            if "/domains/1234" in url:
                return domain_success
            elif "/domains/1235" in url:
                return domain_success_2
            else:
                return domain_not_found

        mock_http_client.get = AsyncMock(side_effect=mock_get)

        client._client = mock_http_client

        result = await client.list_domains()

        # Should have found 2 domains
        assert len(result) == 2
        assert result[0]["name"] == "Domain 1"
        assert result[1]["name"] == "Domain 2"

    @pytest.mark.asyncio
    async def test_list_domains_with_custom_company_id(self, client):
        """Test list_domains uses custom company_id."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 5678, "domains": 0}
        company_response.raise_for_status = MagicMock()

        mock_http_client.request.return_value = company_response
        mock_http_client.get = AsyncMock(return_value=MagicMock(status_code=404))

        client._client = mock_http_client

        result = await client.list_domains(company_id=5678)

        # Should have called company endpoint with custom ID
        mock_http_client.request.assert_called_once()
        call_url = mock_http_client.request.call_args[0][1]
        assert "/companies/5678" in call_url
        assert result == []

    @pytest.mark.asyncio
    async def test_list_domains_handles_exceptions_gracefully(self, client):
        """Test list_domains handles scan exceptions gracefully."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()

        mock_http_client.request.return_value = company_response
        # Simulate network errors during domain scanning
        mock_http_client.get = AsyncMock(side_effect=Exception("Network error"))

        client._client = mock_http_client

        result = await client.list_domains()

        # Should handle errors gracefully and return empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_list_domains_stops_when_count_reached(self, client):
        """Test list_domains stops scanning once domain count is reached."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()

        mock_http_client.request.return_value = company_response

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"id": 1234, "name": "Domain"}
            return response

        mock_http_client.get = AsyncMock(side_effect=mock_get)

        client._client = mock_http_client

        result = await client.list_domains()

        # Should stop after finding 1 domain (the count we expected)
        assert len(result) == 1


class TestGreenImpactAndThirdParties:
    """Tests for green impact and third parties endpoints."""

    @pytest.mark.asyncio
    async def test_get_application_green_impact(self, client):
        """Test get_application_green_impact calls correct endpoint."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"carbonFootprint": 100, "greenIndex": 75}

            result = await client.get_application_green_impact(999)

            mock_get.assert_called_once_with("/applications/999/green")
            assert result["greenIndex"] == 75

    @pytest.mark.asyncio
    async def test_get_application_third_parties(self, client):
        """Test get_application_third_parties calls correct endpoint."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"name": "react", "version": "18.2.0"},
                {"name": "lodash", "version": "4.17.21"},
            ]

            result = await client.get_application_third_parties(888)

            mock_get.assert_called_once_with("/applications/888/thirdParties")
            assert len(result) == 2
            assert result[0]["name"] == "react"


class TestClientClose:
    """Additional tests for client close behavior."""

    @pytest.mark.asyncio
    async def test_close_resets_client_to_none(self, client):
        """Test close sets _client back to None."""
        # Initialize client
        await client._get_client()
        assert client._client is not None

        await client.close()

        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_multiple_times_safe(self, client):
        """Test calling close multiple times is safe."""
        await client._get_client()

        await client.close()
        await client.close()  # Should not raise

        assert client._client is None


class TestListDomainsRateLimiting:
    """Tests for list_domains rate limiting (Issue #13)."""

    @pytest.mark.asyncio
    async def test_list_domains_rejects_negative_delay(self, client):
        """Test list_domains raises ValueError for negative delay."""
        with pytest.raises(ValueError, match="delay must be non-negative"):
            await client.list_domains(delay=-1)

    @pytest.mark.asyncio
    async def test_list_domains_accepts_delay_parameter(self, client):
        """Test list_domains accepts a delay parameter."""
        mock_http_client = AsyncMock()
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 0}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response
        mock_http_client.get = AsyncMock(return_value=MagicMock(status_code=404))
        client._client = mock_http_client

        # Should not raise TypeError
        result = await client.list_domains(delay=0.1)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_domains_calls_sleep_between_requests(self, client):
        """Test list_domains calls asyncio.sleep between requests, not before first."""
        mock_http_client = AsyncMock()
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 2}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        domain_response = MagicMock()
        domain_response.status_code = 200
        domain_response.json.return_value = {"id": 1234, "name": "Domain"}
        mock_http_client.get = AsyncMock(return_value=domain_response)
        client._client = mock_http_client

        with patch("cast_highlight_mcp.client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client.list_domains(delay=0.05)
            # With 2 domains found, sleep should be called once (between 1st and 2nd request)
            # Not before first request
            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_with(0.05)

    @pytest.mark.asyncio
    async def test_list_domains_no_sleep_when_delay_zero(self, client):
        """Test list_domains does not call sleep when delay=0."""
        mock_http_client = AsyncMock()
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        domain_response = MagicMock()
        domain_response.status_code = 200
        domain_response.json.return_value = {"id": 1234, "name": "Domain"}
        mock_http_client.get = AsyncMock(return_value=domain_response)
        client._client = mock_http_client

        with patch("cast_highlight_mcp.client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client.list_domains(delay=0)
            mock_sleep.assert_not_called()


class TestListDomainsLogging:
    """Tests for list_domains exception logging (Issue #14)."""

    @pytest.mark.asyncio
    async def test_list_domains_logs_auth_errors(self, client):
        """Test list_domains logs 401/403 authentication errors."""
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

        with patch("cast_highlight_mcp.client.logger") as mock_logger:
            await client.list_domains()
            # Should log authentication failure
            assert mock_logger.warning.called or mock_logger.debug.called

    @pytest.mark.asyncio
    async def test_list_domains_logs_network_errors(self, client):
        """Test list_domains logs network/connection errors."""
        mock_http_client = AsyncMock()
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response
        mock_http_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        client._client = mock_http_client

        with patch("cast_highlight_mcp.client.logger") as mock_logger:
            await client.list_domains()
            assert mock_logger.debug.called

    @pytest.mark.asyncio
    async def test_list_domains_does_not_log_404(self, client):
        """Test list_domains does NOT log 404 errors (expected during scanning)."""
        mock_http_client = AsyncMock()
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        not_found = MagicMock()
        not_found.status_code = 404
        mock_http_client.get = AsyncMock(return_value=not_found)
        client._client = mock_http_client

        with patch("cast_highlight_mcp.client.logger") as mock_logger:
            await client.list_domains()
            # 404s should NOT trigger warning logs
            mock_logger.warning.assert_not_called()


class TestGetClientThreadSafety:
    """Tests for _get_client thread safety with asyncio.Lock (Issue #12)."""

    @pytest.mark.asyncio
    async def test_client_has_lock_attribute(self, client):
        """Test HighlightClient has a _lock attribute."""
        assert hasattr(client, "_lock"), "HighlightClient should have _lock attribute"

    @pytest.mark.asyncio
    async def test_get_client_uses_lock(self, client):
        """Test _get_client acquires lock during initialization."""
        import asyncio

        # Verify lock exists and is an asyncio.Lock
        assert hasattr(client, "_lock")
        assert isinstance(client._lock, asyncio.Lock)

        await client.close()

    @pytest.mark.asyncio
    async def test_concurrent_get_client_returns_same_instance(self, client):
        """Test concurrent _get_client calls return the same client instance."""
        import asyncio

        # Call _get_client concurrently from multiple tasks
        results = await asyncio.gather(
            client._get_client(),
            client._get_client(),
            client._get_client(),
            client._get_client(),
            client._get_client(),
        )

        # All results should be the same client instance
        assert all(r is results[0] for r in results)

        await client.close()

    @pytest.mark.asyncio
    async def test_close_acquires_lock(self, client):
        """Test close() acquires lock to prevent race conditions."""
        import asyncio

        # Verify lock is used by close
        assert hasattr(client, "_lock")
        assert isinstance(client._lock, asyncio.Lock)

        # Create and close client to verify no deadlock
        await client._get_client()
        await client.close()
        assert client._client is None


class TestListDomainsConsecutiveMisses:
    """Tests for max_consecutive_misses parameter."""

    @pytest.mark.asyncio
    async def test_list_domains_rejects_zero_max_consecutive_misses(self, client):
        """Test list_domains raises ValueError when max_consecutive_misses < 1."""
        with pytest.raises(ValueError, match="max_consecutive_misses must be at least 1"):
            await client.list_domains(max_consecutive_misses=0)

    @pytest.mark.asyncio
    async def test_list_domains_rejects_negative_max_consecutive_misses(self, client):
        """Test list_domains raises ValueError when max_consecutive_misses is negative."""
        with pytest.raises(ValueError, match="max_consecutive_misses must be at least 1"):
            await client.list_domains(max_consecutive_misses=-1)

    @pytest.mark.asyncio
    async def test_list_domains_stops_after_consecutive_misses(self, client):
        """Test list_domains stops scanning after max_consecutive_misses reached."""
        mock_http_client = AsyncMock()

        # Setup company response
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 10}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        # Track get calls - all return 404
        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            return MagicMock(status_code=404)

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        result = await client.list_domains(max_consecutive_misses=3)

        assert result == []
        assert call_count == 3  # Should stop after 3 consecutive misses

    @pytest.mark.asyncio
    async def test_list_domains_resets_consecutive_misses_on_success(self, client):
        """Test consecutive_misses counter resets to 0 after successful response."""
        mock_http_client = AsyncMock()

        # Setup company response - expects 2 domains
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 2}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            # Pattern: 404, 404, 200 (domain 1), 404, 404, 200 (domain 2)
            # If consecutive_misses resets on success, we should find both
            if call_count == 3:
                return MagicMock(
                    status_code=200,
                    json=MagicMock(return_value={"id": 1236, "name": "Domain1"}),
                )
            elif call_count == 6:
                return MagicMock(
                    status_code=200,
                    json=MagicMock(return_value={"id": 1239, "name": "Domain2"}),
                )
            return MagicMock(status_code=404)

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        result = await client.list_domains(max_consecutive_misses=3)

        assert len(result) == 2
        assert call_count == 6  # Found both without early termination

    @pytest.mark.asyncio
    async def test_list_domains_accepts_custom_max_consecutive_misses(self, client):
        """Test list_domains accepts custom max_consecutive_misses value."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 5}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            return MagicMock(status_code=404)

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        await client.list_domains(max_consecutive_misses=7)

        assert call_count == 7  # Should have made exactly 7 requests


class TestListDomainsMaxIterations:
    """Tests for max_iterations parameter (safety limit)."""

    @pytest.mark.asyncio
    async def test_list_domains_uses_default_iteration_limit(self, client):
        """Test list_domains uses max(domain_count * 3, 20) as default limit."""
        mock_http_client = AsyncMock()

        # Company with 5 domains -> limit = max(15, 20) = 20
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 5}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            # Return success to prevent consecutive_misses from stopping early
            # but never find all 5 domains
            if call_count % 4 == 0:  # Only find 1 domain every 4 requests
                return MagicMock(
                    status_code=200,
                    json=MagicMock(
                        return_value={"id": 1234 + call_count, "name": f"D{call_count}"}
                    ),
                )
            return MagicMock(status_code=404)

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        # High consecutive miss threshold so iteration limit is what stops us
        result = await client.list_domains(max_consecutive_misses=100)

        # Should hit iteration limit (20) before finding all 5 domains
        assert call_count == 20
        assert len(result) == 5  # Found 5 domains (at calls 4, 8, 12, 16, 20)

    @pytest.mark.asyncio
    async def test_list_domains_respects_custom_max_iterations(self, client):
        """Test list_domains respects custom max_iterations parameter."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 100}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            # Alternate success/fail to prevent consecutive_misses limit
            if call_count % 2 == 0:
                return MagicMock(
                    status_code=200,
                    json=MagicMock(
                        return_value={"id": 1234 + call_count, "name": f"D{call_count}"}
                    ),
                )
            return MagicMock(status_code=404)

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        result = await client.list_domains(max_iterations=10, max_consecutive_misses=100)

        assert call_count == 10
        assert len(result) == 5  # Found 5 domains in 10 iterations

    @pytest.mark.asyncio
    async def test_list_domains_iteration_limit_prevents_unbounded_scan(self, client):
        """Test iteration limit prevents scanning when domain_count is unrealistically high."""
        mock_http_client = AsyncMock()

        # API reports 1000 domains but they don't exist
        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1000}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            # Every 10th request succeeds to prevent consecutive_misses
            if call_count % 10 == 0:
                return MagicMock(
                    status_code=200,
                    json=MagicMock(
                        return_value={"id": 1234 + call_count, "name": f"D{call_count}"}
                    ),
                )
            return MagicMock(status_code=404)

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        await client.list_domains(max_iterations=50, max_consecutive_misses=20)

        # Should stop at iteration limit, not scan 1000+ IDs
        assert call_count == 50


class TestListDomainsEdgeCases:
    """Edge case tests for list_domains."""

    @pytest.mark.asyncio
    async def test_list_domains_zero_domains_returns_empty_immediately(self, client):
        """Test list_domains returns empty list when company has 0 domains."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 0}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response
        mock_http_client.get = AsyncMock()
        client._client = mock_http_client

        result = await client.list_domains()

        assert result == []
        mock_http_client.get.assert_not_called()  # No scanning should occur

    @pytest.mark.asyncio
    async def test_list_domains_handles_403_status(self, client):
        """Test list_domains handles 403 Forbidden as consecutive miss."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            return MagicMock(status_code=403)

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        result = await client.list_domains(max_consecutive_misses=3)

        assert result == []
        assert call_count == 3  # 403 counts as miss

    @pytest.mark.asyncio
    async def test_list_domains_handles_timeout_exception(self, client):
        """Test list_domains handles httpx.TimeoutException as consecutive miss."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response
        mock_http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        client._client = mock_http_client

        result = await client.list_domains(max_consecutive_misses=2)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_domains_handles_connect_error(self, client):
        """Test list_domains handles httpx.ConnectError as consecutive miss."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 1234, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response
        mock_http_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        client._client = mock_http_client

        result = await client.list_domains(max_consecutive_misses=2)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_domains_starts_at_company_id(self, client):
        """Test list_domains starts scanning from company_id."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 5000, "domains": 1}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        requested_urls = []

        def mock_get(url):
            requested_urls.append(url)
            return MagicMock(
                status_code=200,
                json=MagicMock(return_value={"id": 5000, "name": "Domain"}),
            )

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        await client.list_domains(company_id=5000)

        # First scan request should be for domain ID 5000
        assert "/domains/5000" in requested_urls[0]

    @pytest.mark.asyncio
    async def test_list_domains_scans_forward_only(self, client):
        """Test list_domains only scans IDs >= company_id (forward direction)."""
        mock_http_client = AsyncMock()

        company_response = MagicMock()
        company_response.status_code = 200
        company_response.json.return_value = {"id": 100, "domains": 3}
        company_response.raise_for_status = MagicMock()
        mock_http_client.request.return_value = company_response

        requested_ids = []

        def mock_get(url):
            domain_id = int(url.split("/domains/")[1])
            requested_ids.append(domain_id)
            return MagicMock(
                status_code=200,
                json=MagicMock(return_value={"id": domain_id, "name": f"D{domain_id}"}),
            )

        mock_http_client.get = AsyncMock(side_effect=mock_get)
        client._client = mock_http_client

        await client.list_domains(company_id=100)

        # All requested IDs should be >= company_id (100)
        assert all(id >= 100 for id in requested_ids)
        # IDs should be sequential: 100, 101, 102
        assert requested_ids == [100, 101, 102]
