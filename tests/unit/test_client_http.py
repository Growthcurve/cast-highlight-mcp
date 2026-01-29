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
        with patch.object(
            client, "_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"result": "data"}

            result = await client.get("/companies/1")

            mock_request.assert_called_once_with("GET", "/companies/1")
            assert result == {"result": "data"}

    @pytest.mark.asyncio
    async def test_get_passes_kwargs(self, client):
        """Test get() passes kwargs to _request."""
        with patch.object(
            client, "_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {}

            await client.get("/search", params={"q": "test"})

            mock_request.assert_called_once_with(
                "GET", "/search", params={"q": "test"}
            )


class TestListDomainsScanning:
    """Tests for list_domains domain scanning logic."""

    @pytest.mark.asyncio
    async def test_list_domains_scans_for_domains(self, client):
        """Test list_domains scans ID range for accessible domains."""
        mock_http_client = AsyncMock()

        # Company response with 2 domains
        company_response = MagicMock()
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
