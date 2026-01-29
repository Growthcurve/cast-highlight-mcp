"""Tests for CAST Highlight API client."""

import pytest
from unittest.mock import AsyncMock, patch

from cast_highlight_mcp.client import HighlightClient
from cast_highlight_mcp.config import Config


class TestHighlightClient:
    """Tests for HighlightClient class."""

    def test_client_initialization(self, mock_config):
        """Test client initializes correctly."""
        client = HighlightClient(mock_config)
        assert client.config == mock_config
        assert client.base_url == "https://app.casthighlight.com/WS2"
        assert client._client is None

    def test_client_strips_trailing_slash(self):
        """Test client strips trailing slash from base URL."""
        config = Config(
            base_url="https://example.com/api/",
            access_token="token",
            company_id=1,
        )
        client = HighlightClient(config)
        assert client.base_url == "https://example.com/api"

    def test_headers_property(self, mock_config):
        """Test headers include authorization."""
        client = HighlightClient(mock_config)
        headers = client.headers
        assert headers["Authorization"] == "Bearer test-token-12345"
        assert headers["Accept"] == "application/json"


class TestHighlightClientRequests:
    """Tests for HighlightClient API requests."""

    @pytest.fixture
    def client(self, mock_config):
        return HighlightClient(mock_config)

    @pytest.mark.asyncio
    async def test_get_company(self, client, sample_company_response):
        """Test getting company details."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_company_response

            result = await client.get_company()

            mock_get.assert_called_once_with("/companies/1234")
            assert result["id"] == 1234
            assert result["name"] == "Test Company"

    @pytest.mark.asyncio
    async def test_get_company_with_custom_id(self, client, sample_company_response):
        """Test getting company with custom ID."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_company_response

            await client.get_company(company_id=5678)

            mock_get.assert_called_once_with("/companies/5678")

    @pytest.mark.asyncio
    async def test_get_domain(self, client, sample_domain_response):
        """Test getting domain details."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_domain_response

            result = await client.get_domain(1234)

            mock_get.assert_called_once_with("/domains/1234")
            assert result["name"] == "Test Domain"

    @pytest.mark.asyncio
    async def test_get_domain_applications(self, client, sample_application_response):
        """Test getting applications in a domain."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [sample_application_response]

            result = await client.get_domain_applications(1234)

            mock_get.assert_called_once_with("/domains/1234/applications")
            assert len(result) == 1
            assert result[0]["name"] == "Test Application"

    @pytest.mark.asyncio
    async def test_get_application(self, client, sample_application_response):
        """Test getting application details."""
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_application_response

            result = await client.get_application(5678)

            mock_get.assert_called_once_with("/applications/5678")
            assert result["id"] == 5678

    @pytest.mark.asyncio
    async def test_get_application_metrics(self, client):
        """Test getting application metrics."""
        metrics = {"softwareHealth": 0.85}
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = metrics

            result = await client.get_application_metrics(5678)

            mock_get.assert_called_once_with("/applications/5678/metrics")
            assert result["softwareHealth"] == 0.85

    @pytest.mark.asyncio
    async def test_get_application_technologies(self, client):
        """Test getting application technologies."""
        technologies = [{"technology": "Java", "totalLinesOfCode": 10000}]
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = technologies

            result = await client.get_application_technologies(5678)

            mock_get.assert_called_once_with("/applications/5678/technologies")
            assert result[0]["technology"] == "Java"

    @pytest.mark.asyncio
    async def test_get_application_cloud_readiness(self, client):
        """Test getting cloud readiness assessment."""
        cloud_data = {"cloudReady": 0.75, "blockers": 5}
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = cloud_data

            result = await client.get_application_cloud_readiness(5678)

            mock_get.assert_called_once_with("/applications/5678/cloudReady")
            assert result["cloudReady"] == 0.75

    @pytest.mark.asyncio
    async def test_get_application_cves(self, client):
        """Test getting application CVEs."""
        cves = [{"name": "CVE-2024-1234", "cvssScore": 9.8}]
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = cves

            result = await client.get_application_cves(5678)

            mock_get.assert_called_once_with("/applications/5678/cve")
            assert result[0]["name"] == "CVE-2024-1234"

    @pytest.mark.asyncio
    async def test_get_benchmark(self, client):
        """Test getting benchmark data."""
        benchmark = {"averageHealth": 0.72, "totalApplications": 50000}
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = benchmark

            result = await client.get_benchmark()

            mock_get.assert_called_once_with("/benchmark")
            assert result["averageHealth"] == 0.72

    @pytest.mark.asyncio
    async def test_close_client(self, client):
        """Test closing the HTTP client."""
        mock_http_client = AsyncMock()
        client._client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_client_when_none(self, client):
        """Test closing when client is already None."""
        assert client._client is None
        await client.close()  # Should not raise
        assert client._client is None


class TestHighlightClientContextManager:
    """Tests for HighlightClient async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_enter(self, mock_config):
        """Test async context manager returns client on enter."""
        client = HighlightClient(mock_config)
        async with client as ctx:
            assert ctx is client

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exit(self, mock_config):
        """Test async context manager closes client on exit."""
        client = HighlightClient(mock_config)
        mock_http_client = AsyncMock()
        client._client = mock_http_client

        async with client:
            pass

        mock_http_client.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self, mock_config):
        """Test async context manager closes client even on exception."""
        client = HighlightClient(mock_config)
        mock_http_client = AsyncMock()
        client._client = mock_http_client

        with pytest.raises(ValueError):
            async with client:
                raise ValueError("Test error")

        mock_http_client.aclose.assert_called_once()
        assert client._client is None
