"""Tests for MCP server call_tool handler."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cast_highlight_mcp import server
from cast_highlight_mcp.server import call_tool, get_client


class TestGetClient:
    """Tests for get_client function."""

    def test_get_client_raises_when_not_initialized(self):
        """Test get_client raises RuntimeError when client is not initialized."""
        # Ensure client is not initialized
        original_client = server._client
        server._client = None

        try:
            with pytest.raises(RuntimeError, match="Client not initialized"):
                get_client()
        finally:
            # Restore original state
            server._client = original_client

    def test_get_client_returns_existing_client(self):
        """Test get_client returns existing client if available."""
        original_client = server._client
        mock_existing_client = MagicMock()
        server._client = mock_existing_client

        try:
            result = get_client()
            assert result is mock_existing_client
        finally:
            # Restore original state
            server._client = original_client


class TestCallToolGetCompany:
    """Tests for highlight_get_company tool."""

    @pytest.mark.asyncio
    async def test_get_company_success(self):
        """Test highlight_get_company returns company data."""
        mock_client = AsyncMock()
        mock_client.get_company.return_value = {"id": 1234, "name": "Test Co"}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {})

        assert len(result) == 1
        assert result[0].type == "text"
        data = json.loads(result[0].text)
        assert data["id"] == 1234
        mock_client.get_company.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_get_company_with_custom_id(self):
        """Test highlight_get_company with custom company_id."""
        mock_client = AsyncMock()
        mock_client.get_company.return_value = {"id": 5678}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {"company_id": 5678})

        mock_client.get_company.assert_called_once_with(5678)
        data = json.loads(result[0].text)
        assert data["id"] == 5678


class TestCallToolListDomains:
    """Tests for highlight_list_domains tool."""

    @pytest.mark.asyncio
    async def test_list_domains_success(self):
        """Test highlight_list_domains returns domain list."""
        mock_client = AsyncMock()
        mock_client.list_domains.return_value = [{"id": 1, "name": "Domain 1"}]

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_list_domains", {})

        mock_client.list_domains.assert_called_once_with(None)
        data = json.loads(result[0].text)
        assert len(data) == 1
        assert data[0]["name"] == "Domain 1"

    @pytest.mark.asyncio
    async def test_list_domains_with_company_id(self):
        """Test highlight_list_domains with company_id."""
        mock_client = AsyncMock()
        mock_client.list_domains.return_value = []

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool("highlight_list_domains", {"company_id": 9999})

        mock_client.list_domains.assert_called_once_with(9999)


class TestCallToolGetDomain:
    """Tests for highlight_get_domain tool."""

    @pytest.mark.asyncio
    async def test_get_domain_success(self):
        """Test highlight_get_domain returns domain details."""
        mock_client = AsyncMock()
        mock_client.get_domain.return_value = {"id": 123, "name": "My Domain"}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_domain", {"domain_id": 123})

        mock_client.get_domain.assert_called_once_with(123)
        data = json.loads(result[0].text)
        assert data["name"] == "My Domain"


class TestCallToolListApplications:
    """Tests for highlight_list_applications tool."""

    @pytest.mark.asyncio
    async def test_list_applications_success(self):
        """Test highlight_list_applications returns app list."""
        mock_client = AsyncMock()
        mock_client.get_domain_applications.return_value = [
            {"id": 1, "name": "App1"},
            {"id": 2, "name": "App2"},
        ]

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_list_applications", {"domain_id": 100})

        mock_client.get_domain_applications.assert_called_once_with(100)
        data = json.loads(result[0].text)
        assert len(data) == 2


class TestCallToolGetApplication:
    """Tests for highlight_get_application tool."""

    @pytest.mark.asyncio
    async def test_get_application_success(self):
        """Test highlight_get_application returns app details."""
        mock_client = AsyncMock()
        mock_client.get_application.return_value = {"id": 5678, "name": "TestApp"}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_application", {"application_id": 5678})

        mock_client.get_application.assert_called_once_with(5678)
        data = json.loads(result[0].text)
        assert data["id"] == 5678


class TestCallToolGetMetrics:
    """Tests for highlight_get_metrics tool."""

    @pytest.mark.asyncio
    async def test_get_metrics_success(self):
        """Test highlight_get_metrics returns health metrics."""
        mock_client = AsyncMock()
        mock_client.get_application_metrics.return_value = {
            "softwareHealth": 0.85,
            "softwareAgility": 0.75,
        }

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_metrics", {"application_id": 999})

        mock_client.get_application_metrics.assert_called_once_with(999)
        data = json.loads(result[0].text)
        assert data["softwareHealth"] == 0.85


class TestCallToolGetTechnologies:
    """Tests for highlight_get_technologies tool."""

    @pytest.mark.asyncio
    async def test_get_technologies_success(self):
        """Test highlight_get_technologies returns tech breakdown."""
        mock_client = AsyncMock()
        mock_client.get_application_technologies.return_value = [
            {"technology": "Python", "linesOfCode": 5000}
        ]

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_technologies", {"application_id": 100})

        mock_client.get_application_technologies.assert_called_once_with(100)
        data = json.loads(result[0].text)
        assert data[0]["technology"] == "Python"


class TestCallToolGetCloudReadiness:
    """Tests for highlight_get_cloud_readiness tool."""

    @pytest.mark.asyncio
    async def test_get_cloud_readiness_success(self):
        """Test highlight_get_cloud_readiness returns cloud assessment."""
        mock_client = AsyncMock()
        mock_client.get_application_cloud_readiness.return_value = {
            "cloudReadyScore": 75,
            "blockers": 3,
        }

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_cloud_readiness", {"application_id": 200})

        mock_client.get_application_cloud_readiness.assert_called_once_with(200)
        data = json.loads(result[0].text)
        assert data["cloudReadyScore"] == 75


class TestCallToolGetGreenImpact:
    """Tests for highlight_get_green_impact tool."""

    @pytest.mark.asyncio
    async def test_get_green_impact_success(self):
        """Test highlight_get_green_impact returns environmental metrics."""
        mock_client = AsyncMock()
        mock_client.get_application_green_impact.return_value = {
            "carbonFootprint": 120.5,
            "greenScore": 65,
        }

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_green_impact", {"application_id": 300})

        mock_client.get_application_green_impact.assert_called_once_with(300)
        data = json.loads(result[0].text)
        assert data["greenScore"] == 65


class TestCallToolGetCVEs:
    """Tests for highlight_get_cves tool."""

    @pytest.mark.asyncio
    async def test_get_cves_success(self):
        """Test highlight_get_cves returns vulnerability list."""
        mock_client = AsyncMock()
        mock_client.get_application_cves.return_value = [
            {"cve": "CVE-2024-1234", "severity": "HIGH", "cvss": 9.1}
        ]

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_cves", {"application_id": 400})

        mock_client.get_application_cves.assert_called_once_with(400)
        data = json.loads(result[0].text)
        assert data[0]["cve"] == "CVE-2024-1234"


class TestCallToolGetThirdParties:
    """Tests for highlight_get_third_parties tool."""

    @pytest.mark.asyncio
    async def test_get_third_parties_success(self):
        """Test highlight_get_third_parties returns component list."""
        mock_client = AsyncMock()
        mock_client.get_application_third_parties.return_value = [
            {"name": "lodash", "version": "4.17.21", "license": "MIT"}
        ]

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_third_parties", {"application_id": 500})

        mock_client.get_application_third_parties.assert_called_once_with(500)
        data = json.loads(result[0].text)
        assert data[0]["name"] == "lodash"


class TestCallToolGetBenchmark:
    """Tests for highlight_get_benchmark tool."""

    @pytest.mark.asyncio
    async def test_get_benchmark_success(self):
        """Test highlight_get_benchmark returns global benchmark data."""
        mock_client = AsyncMock()
        mock_client.get_benchmark.return_value = {
            "totalApplications": 50000,
            "averageHealth": 0.72,
        }

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_benchmark", {})

        mock_client.get_benchmark.assert_called_once()
        data = json.loads(result[0].text)
        assert data["totalApplications"] == 50000


class TestCallToolErrorHandling:
    """Tests for call_tool error handling."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Test unknown tool name returns error message."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("unknown_tool", {})

        assert len(result) == 1
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_exception_returns_error_message(self):
        """Test exception is caught and returns error message."""
        mock_client = AsyncMock()
        mock_client.get_company.side_effect = Exception("API connection failed")

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {})

        assert len(result) == 1
        assert "Error: API connection failed" in result[0].text

    @pytest.mark.asyncio
    async def test_key_error_for_missing_required_argument(self):
        """Test KeyError for missing required argument is caught."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_domain", {})

        assert len(result) == 1
        assert "Error:" in result[0].text

    @pytest.mark.asyncio
    async def test_http_error_is_caught(self):
        """Test HTTP errors are caught and returned as error message."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_application.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_application", {"application_id": 99999})

        assert len(result) == 1
        assert "Error:" in result[0].text
