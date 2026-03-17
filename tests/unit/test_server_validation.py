"""Tests for input validation in call_tool handler."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from cast_highlight_mcp.server import call_tool


class TestCallToolValidationGetCompany:
    """Tests for validation in highlight_get_company tool."""

    @pytest.mark.asyncio
    async def test_valid_company_id(self):
        """Test valid company_id is accepted."""
        mock_client = AsyncMock()
        mock_client.get_company.return_value = {"id": 1234}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {"company_id": 1234})

        mock_client.get_company.assert_called_once_with(1234)
        data = json.loads(result[0].text)
        assert data["id"] == 1234

    @pytest.mark.asyncio
    async def test_zero_company_id_fails(self):
        """Test zero company_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {"company_id": 0})

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "positive" in result[0].text
        mock_client.get_company.assert_not_called()

    @pytest.mark.asyncio
    async def test_negative_company_id_fails(self):
        """Test negative company_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {"company_id": -5})

        assert "Validation error" in result[0].text
        mock_client.get_company.assert_not_called()

    @pytest.mark.asyncio
    async def test_string_company_id_fails(self):
        """Test non-numeric string company_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {"company_id": "invalid"})

        assert "Validation error" in result[0].text
        mock_client.get_company.assert_not_called()


class TestCallToolValidationGetDomain:
    """Tests for validation in highlight_get_domain tool."""

    @pytest.mark.asyncio
    async def test_valid_domain_id(self):
        """Test valid domain_id is accepted."""
        mock_client = AsyncMock()
        mock_client.get_domain.return_value = {"id": 123, "name": "Test"}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool("highlight_get_domain", {"domain_id": 123})

        mock_client.get_domain.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_missing_domain_id_fails(self):
        """Test missing domain_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_domain", {})

        assert "Validation error" in result[0].text
        assert "required" in result[0].text
        mock_client.get_domain.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_domain_id_fails(self):
        """Test zero domain_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_domain", {"domain_id": 0})

        assert "Validation error" in result[0].text
        mock_client.get_domain.assert_not_called()

    @pytest.mark.asyncio
    async def test_negative_domain_id_fails(self):
        """Test negative domain_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_domain", {"domain_id": -100})

        assert "Validation error" in result[0].text
        mock_client.get_domain.assert_not_called()


class TestCallToolValidationListApplications:
    """Tests for validation in highlight_list_applications tool."""

    @pytest.mark.asyncio
    async def test_valid_domain_id(self):
        """Test valid domain_id is accepted."""
        mock_client = AsyncMock()
        mock_client.get_domain_applications.return_value = []

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool("highlight_list_applications", {"domain_id": 456})

        mock_client.get_domain_applications.assert_called_once_with(456)

    @pytest.mark.asyncio
    async def test_missing_domain_id_fails(self):
        """Test missing domain_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_list_applications", {})

        assert "Validation error" in result[0].text
        mock_client.get_domain_applications.assert_not_called()


class TestCallToolValidationGetApplication:
    """Tests for validation in highlight_get_application tool."""

    @pytest.mark.asyncio
    async def test_valid_args(self):
        """Test valid domain_id and application_id are accepted."""
        mock_client = AsyncMock()
        mock_client.get_application.return_value = {"id": 789}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool(
                "highlight_get_application",
                {"domain_id": 100, "application_id": 789},
            )

        mock_client.get_application.assert_called_once_with(100, 789)

    @pytest.mark.asyncio
    async def test_missing_application_id_fails(self):
        """Test missing application_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_application", {"domain_id": 100})

        assert "Validation error" in result[0].text
        assert "required" in result[0].text
        mock_client.get_application.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_domain_id_fails(self):
        """Test missing domain_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_application", {"application_id": 789})

        assert "Validation error" in result[0].text
        assert "required" in result[0].text
        mock_client.get_application.assert_not_called()

    @pytest.mark.asyncio
    async def test_zero_application_id_fails(self):
        """Test zero application_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool(
                "highlight_get_application",
                {"domain_id": 100, "application_id": 0},
            )

        assert "Validation error" in result[0].text
        mock_client.get_application.assert_not_called()

    @pytest.mark.asyncio
    async def test_negative_application_id_fails(self):
        """Test negative application_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool(
                "highlight_get_application",
                {"domain_id": 100, "application_id": -1},
            )

        assert "Validation error" in result[0].text
        mock_client.get_application.assert_not_called()

    @pytest.mark.asyncio
    async def test_boolean_application_id_fails(self):
        """Test boolean application_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool(
                "highlight_get_application",
                {"domain_id": 100, "application_id": True},
            )

        assert "Validation error" in result[0].text
        mock_client.get_application.assert_not_called()


class TestCallToolValidationGetMetrics:
    """Tests for validation in highlight_get_metrics tool."""

    @pytest.mark.asyncio
    async def test_valid_args(self):
        """Test valid domain_id and application_id are accepted."""
        mock_client = AsyncMock()
        mock_client.get_application_metrics.return_value = {"softwareHealth": 0.8}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool(
                "highlight_get_metrics",
                {"domain_id": 50, "application_id": 100},
            )

        mock_client.get_application_metrics.assert_called_once_with(50, 100)

    @pytest.mark.asyncio
    async def test_missing_application_id_fails(self):
        """Test missing application_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_metrics", {"domain_id": 50})

        assert "Validation error" in result[0].text
        mock_client.get_application_metrics.assert_not_called()


class TestCallToolValidationGetComponents:
    """Tests for validation in highlight_get_components tool."""

    @pytest.mark.asyncio
    async def test_valid_args(self):
        """Test valid domain_id and application_id are accepted."""
        mock_client = AsyncMock()
        mock_client.get_application_components.return_value = []

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool(
                "highlight_get_components",
                {"domain_id": 50, "application_id": 200},
            )

        mock_client.get_application_components.assert_called_once_with(50, 200)

    @pytest.mark.asyncio
    async def test_invalid_application_id_fails(self):
        """Test invalid application_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool(
                "highlight_get_components",
                {"domain_id": 50, "application_id": -50},
            )

        assert "Validation error" in result[0].text
        mock_client.get_application_components.assert_not_called()


class TestCallToolValidationGetCloudReadiness:
    """Tests for validation in highlight_get_cloud_readiness tool."""

    @pytest.mark.asyncio
    async def test_valid_args(self):
        """Test valid domain_id and application_id are accepted."""
        mock_client = AsyncMock()
        mock_client.get_application_cloud_readiness.return_value = {"cloudReady": True}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool(
                "highlight_get_cloud_readiness",
                {"domain_id": 50, "application_id": 300},
            )

        mock_client.get_application_cloud_readiness.assert_called_once_with(50, 300)

    @pytest.mark.asyncio
    async def test_invalid_application_id_fails(self):
        """Test invalid application_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool(
                "highlight_get_cloud_readiness",
                {"domain_id": 50, "application_id": "bad"},
            )

        assert "Validation error" in result[0].text
        mock_client.get_application_cloud_readiness.assert_not_called()


class TestCallToolValidationGetCVEs:
    """Tests for validation in highlight_get_cves tool."""

    @pytest.mark.asyncio
    async def test_valid_domain_id(self):
        """Test valid domain_id is accepted."""
        mock_client = AsyncMock()
        mock_client.get_domain_cves.return_value = []

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool("highlight_get_cves", {"domain_id": 50})

        mock_client.get_domain_cves.assert_called_once_with(50)

    @pytest.mark.asyncio
    async def test_missing_domain_id_fails(self):
        """Test missing domain_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_cves", {})

        assert "Validation error" in result[0].text
        mock_client.get_domain_cves.assert_not_called()


class TestCallToolValidationListDomains:
    """Tests for validation in highlight_list_domains tool."""

    @pytest.mark.asyncio
    async def test_valid_company_id(self):
        """Test valid company_id is accepted."""
        mock_client = AsyncMock()
        mock_client.list_domains.return_value = []

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool("highlight_list_domains", {"company_id": 1000})

        mock_client.list_domains.assert_called_once_with(1000)

    @pytest.mark.asyncio
    async def test_missing_company_id_uses_none(self):
        """Test missing company_id passes None to client."""
        mock_client = AsyncMock()
        mock_client.list_domains.return_value = []

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool("highlight_list_domains", {})

        mock_client.list_domains.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_invalid_company_id_fails(self):
        """Test invalid company_id is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_list_domains", {"company_id": -999})

        assert "Validation error" in result[0].text
        mock_client.list_domains.assert_not_called()


class TestCallToolValidationBenchmark:
    """Tests for validation in highlight_get_benchmark tool (no args)."""

    @pytest.mark.asyncio
    async def test_empty_args_succeeds(self):
        """Test tool works with empty arguments."""
        mock_client = AsyncMock()
        mock_client.get_benchmark.return_value = {"total": 50000}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_benchmark", {})

        mock_client.get_benchmark.assert_called_once()
        data = json.loads(result[0].text)
        assert data["total"] == 50000


class TestCallToolValidationEdgeCases:
    """Tests for edge cases in validation."""

    @pytest.mark.asyncio
    async def test_string_numeric_id_is_converted(self):
        """Test string numeric ID is converted to integer."""
        mock_client = AsyncMock()
        mock_client.get_application.return_value = {"id": 123}

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            await call_tool(
                "highlight_get_application",
                {"domain_id": 50, "application_id": "123"},
            )

        # Should be converted to integer
        mock_client.get_application.assert_called_once_with(50, 123)

    @pytest.mark.asyncio
    async def test_very_large_id_fails(self):
        """Test very large ID exceeding max value fails."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool(
                "highlight_get_application",
                {"domain_id": 50, "application_id": 2**32},
            )

        assert "Validation error" in result[0].text
        assert "exceeds maximum" in result[0].text
        mock_client.get_application.assert_not_called()

    @pytest.mark.asyncio
    async def test_float_id_fails(self):
        """Test float ID is rejected."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool(
                "highlight_get_application",
                {"domain_id": 50, "application_id": 123.5},
            )

        assert "Validation error" in result[0].text
        mock_client.get_application.assert_not_called()
