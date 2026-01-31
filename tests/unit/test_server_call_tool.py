"""Tests for MCP server call_tool handler."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cast_highlight_mcp import server
from cast_highlight_mcp.server import _extract_api_version, call_tool, get_client, get_config


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


class TestGetConfig:
    """Tests for get_config function."""

    def test_get_config_raises_when_not_loaded(self):
        """Test get_config raises RuntimeError when config is not loaded."""
        original_config = server._config
        server._config = None

        try:
            with pytest.raises(RuntimeError, match="Config not loaded"):
                get_config()
        finally:
            server._config = original_config

    def test_get_config_returns_existing_config(self):
        """Test get_config returns existing config if available."""
        original_config = server._config
        mock_config = MagicMock()
        server._config = mock_config

        try:
            result = get_config()
            assert result is mock_config
        finally:
            server._config = original_config


class TestExtractApiVersion:
    """Tests for _extract_api_version function."""

    def test_extract_ws2_from_standard_url(self):
        """Test extracting WS2 from standard CAST Highlight URL."""
        url = "https://app.casthighlight.com/WS2"
        assert _extract_api_version(url) == "WS2"

    def test_extract_version_from_nested_path(self):
        """Test extracting version from nested path like /api/v2."""
        url = "https://api.example.com/api/v2"
        assert _extract_api_version(url) == "v2"

    def test_extract_version_v1(self):
        """Test extracting v1 version."""
        url = "https://api.example.com/v1"
        assert _extract_api_version(url) == "v1"

    def test_extract_returns_unknown_for_no_path(self):
        """Test returns 'unknown' when URL has no path."""
        url = "https://api.example.com"
        assert _extract_api_version(url) == "unknown"

    def test_extract_returns_unknown_for_root_path(self):
        """Test returns 'unknown' when URL has only root path."""
        url = "https://api.example.com/"
        assert _extract_api_version(url) == "unknown"

    def test_extract_handles_trailing_slash(self):
        """Test extracting version when URL has trailing slash."""
        url = "https://app.casthighlight.com/WS2/"
        assert _extract_api_version(url) == "WS2"

    def test_extract_with_query_params(self):
        """Test extracting version with query parameters present."""
        url = "https://app.casthighlight.com/WS2?token=abc"
        assert _extract_api_version(url) == "WS2"

    def test_extract_custom_api_version(self):
        """Test extracting custom API version identifier."""
        url = "https://custom.api.com/rest/v3-beta"
        assert _extract_api_version(url) == "v3-beta"


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
    async def test_exception_returns_sanitized_error_message(self):
        """Test generic exception is caught and returns sanitized error message."""
        mock_client = AsyncMock()
        mock_client.get_company.side_effect = Exception("API connection failed with sensitive URL")

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {})

        assert len(result) == 1
        # Should NOT contain the raw exception message
        assert "API connection failed" not in result[0].text
        assert "sensitive URL" not in result[0].text
        # Should contain the sanitized message
        assert "An unexpected error occurred" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_required_argument_returns_validation_error(self):
        """Test missing required argument returns validation error message."""
        mock_client = AsyncMock()

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_domain", {})

        assert len(result) == 1
        assert "Validation error" in result[0].text
        assert "domain_id" in result[0].text
        assert "required" in result[0].text

    @pytest.mark.asyncio
    async def test_http_404_error_returns_sanitized_message(self):
        """Test HTTP 404 error returns sanitized message without URL details."""
        import httpx

        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/sensitive/path/with/tokens"
        mock_response = MagicMock(status_code=404)

        mock_client = AsyncMock()
        mock_client.get_application.side_effect = httpx.HTTPStatusError(
            "404 Not Found for url: https://api.example.com/sensitive/path",
            request=mock_request,
            response=mock_response,
        )

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_application", {"application_id": 99999})

        assert len(result) == 1
        # Should NOT contain URL or sensitive details
        assert "example.com" not in result[0].text
        assert "sensitive" not in result[0].text
        # Should contain sanitized message
        assert "API error: Resource not found (404)" in result[0].text

    @pytest.mark.asyncio
    async def test_http_401_error_returns_sanitized_message(self):
        """Test HTTP 401 error returns sanitized authentication error."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized: Invalid token xyz123",
            request=MagicMock(),
            response=MagicMock(status_code=401),
        )

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {})

        assert len(result) == 1
        assert "xyz123" not in result[0].text  # Token should not leak
        assert "API error: Authentication failed (401)" in result[0].text

    @pytest.mark.asyncio
    async def test_http_500_error_returns_sanitized_message(self):
        """Test HTTP 500 error returns sanitized server error."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error: Database connection string exposed",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {})

        assert len(result) == 1
        assert "Database" not in result[0].text
        assert "API error: Server error (500)" in result[0].text

    @pytest.mark.asyncio
    async def test_timeout_error_returns_sanitized_message(self):
        """Test timeout error returns sanitized network error message."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.TimeoutException(
            "Connection to https://api.secret.com/internal timed out"
        )

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {})

        assert len(result) == 1
        assert "secret.com" not in result[0].text
        assert "Network error: Request timed out" in result[0].text

    @pytest.mark.asyncio
    async def test_connect_error_returns_sanitized_message(self):
        """Test connection error returns sanitized network error message."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.ConnectError(
            "Failed to connect to internal.api.server:8443"
        )

        with patch("cast_highlight_mcp.server.get_client", return_value=mock_client):
            result = await call_tool("highlight_get_company", {})

        assert len(result) == 1
        assert "internal.api.server" not in result[0].text
        assert "8443" not in result[0].text
        assert "Network error: Unable to connect to CAST Highlight API" in result[0].text


class TestSanitizeErrorMessage:
    """Tests for _sanitize_error_message function."""

    def test_http_status_error_401(self):
        """Test HTTP 401 returns authentication failed message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401),
        )
        result = _sanitize_error_message(error)
        assert result == "API error: Authentication failed (401)"

    def test_http_status_error_403(self):
        """Test HTTP 403 returns access forbidden message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=MagicMock(status_code=403),
        )
        result = _sanitize_error_message(error)
        assert result == "API error: Access forbidden (403)"

    def test_http_status_error_404(self):
        """Test HTTP 404 returns resource not found message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        result = _sanitize_error_message(error)
        assert result == "API error: Resource not found (404)"

    def test_http_status_error_429(self):
        """Test HTTP 429 returns rate limit exceeded message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )
        result = _sanitize_error_message(error)
        assert result == "API error: Rate limit exceeded (429)"

    def test_http_status_error_4xx_generic(self):
        """Test generic 4xx returns client error message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.HTTPStatusError(
            "400 Bad Request",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )
        result = _sanitize_error_message(error)
        assert result == "API error: Client error (400)"

    def test_http_status_error_5xx(self):
        """Test 5xx returns server error message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.HTTPStatusError(
            "502 Bad Gateway",
            request=MagicMock(),
            response=MagicMock(status_code=502),
        )
        result = _sanitize_error_message(error)
        assert result == "API error: Server error (502)"

    def test_timeout_exception(self):
        """Test TimeoutException returns sanitized timeout message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.TimeoutException("Connection to api.server.com timed out")
        result = _sanitize_error_message(error)
        assert result == "Network error: Request timed out"
        assert "api.server.com" not in result

    def test_connect_error(self):
        """Test ConnectError returns sanitized connection message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.ConnectError("Failed to connect to internal-server:8443")
        result = _sanitize_error_message(error)
        assert result == "Network error: Unable to connect to CAST Highlight API"
        assert "internal-server" not in result

    def test_request_error(self):
        """Test generic RequestError returns sanitized network message."""
        import httpx
        from cast_highlight_mcp.server import _sanitize_error_message

        error = httpx.RequestError("SSL certificate verification failed for private.api.com")
        result = _sanitize_error_message(error)
        assert result == "Network error: Failed to communicate with CAST Highlight API"
        assert "private.api.com" not in result
        assert "SSL" not in result

    def test_value_error(self):
        """Test ValueError returns sanitized validation message."""
        from cast_highlight_mcp.server import _sanitize_error_message

        error = ValueError("Invalid company_id: user_provided_value_123")
        result = _sanitize_error_message(error)
        assert result == "Validation error: Invalid argument value"
        assert "user_provided_value_123" not in result

    def test_key_error(self):
        """Test KeyError returns message with key name."""
        from cast_highlight_mcp.server import _sanitize_error_message

        error = KeyError("application_id")
        result = _sanitize_error_message(error)
        assert result == "Missing required argument: application_id"

    def test_runtime_error_not_initialized(self):
        """Test RuntimeError for uninitialized client."""
        from cast_highlight_mcp.server import _sanitize_error_message

        error = RuntimeError("Client not initialized. Server lifecycle not started.")
        result = _sanitize_error_message(error)
        assert result == "Server error: Service not ready"

    def test_runtime_error_generic(self):
        """Test generic RuntimeError returns unexpected error."""
        from cast_highlight_mcp.server import _sanitize_error_message

        error = RuntimeError("Something went wrong with internal path /var/secret")
        result = _sanitize_error_message(error)
        assert result == "An unexpected error occurred"
        assert "/var/secret" not in result

    def test_generic_exception(self):
        """Test unknown exception type returns generic message."""
        from cast_highlight_mcp.server import _sanitize_error_message

        error = Exception("Detailed internal error: database password is xyz123")
        result = _sanitize_error_message(error)
        assert result == "An unexpected error occurred"
        assert "xyz123" not in result
        assert "password" not in result

    def test_validation_error_message_is_safe(self):
        """Test ValidationError returns sanitized message with field name.

        ValidationError messages are considered safe because they are
        generated by our validation code and do not contain raw user input.
        """
        from cast_highlight_mcp.server import _sanitize_error_message
        from cast_highlight_mcp.validation import ValidationError

        error = ValidationError("domain_id", "must be a positive integer")
        result = _sanitize_error_message(error)
        assert result == "Validation error: must be a positive integer (field: domain_id)"

    def test_validation_error_does_not_leak_user_input(self):
        """Test that ValidationError messages don't expose raw user input.

        Even if a ValidationError is manually created with user input,
        our validation functions should never include raw user values.
        This test verifies the guarantee.
        """
        from cast_highlight_mcp.validation import validate_positive_integer, ValidationError

        # Simulate what would happen with malicious input
        malicious_value = "<script>alert('xss')</script>"

        try:
            validate_positive_integer(malicious_value, "domain_id")
        except ValidationError as e:
            # The error message should NOT contain the malicious input
            assert malicious_value not in e.message
            assert malicious_value not in str(e)
            # It should have a generic message
            assert "must be a valid integer" in e.message


class TestCallToolHealthCheck:
    """Tests for highlight_health_check tool."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config with standard base_url."""
        config = MagicMock()
        config.base_url = "https://app.casthighlight.com/WS2"
        return config

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_config):
        """Test highlight_health_check returns healthy status when API is accessible."""
        mock_client = AsyncMock()
        mock_client.get_company.return_value = {
            "id": 1234,
            "name": "Test Company",
            "status": "active",
        }

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        assert len(result) == 1
        assert result[0].type == "text"
        data = json.loads(result[0].text)
        assert data["status"] == "healthy"
        assert data["company_name"] == "Test Company"
        assert data["company_id"] == 1234
        assert data["api_version"] == "WS2"
        assert data["message"] == "Successfully connected to CAST Highlight API"
        mock_client.get_company.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_connection_error(self, mock_config):
        """Test highlight_health_check returns unhealthy status on connection error."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.ConnectError(
            "Failed to connect to api.casthighlight.com"
        )

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["status"] == "unhealthy"
        assert data["company_name"] is None
        assert data["company_id"] is None
        assert data["api_version"] == "WS2"
        assert "Unable to connect" in data["message"]

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_auth_error(self, mock_config):
        """Test highlight_health_check returns unhealthy status on authentication error."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401),
        )

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["status"] == "unhealthy"
        assert data["company_name"] is None
        assert data["company_id"] is None
        assert "Authentication failed" in data["message"]

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_timeout(self, mock_config):
        """Test highlight_health_check returns unhealthy status on timeout."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.TimeoutException("Connection timed out")

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["status"] == "unhealthy"
        assert data["company_name"] is None
        assert "timed out" in data["message"]

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_server_error(self, mock_config):
        """Test highlight_health_check returns unhealthy status on server error."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["status"] == "unhealthy"
        assert "Server error" in data["message"]

    @pytest.mark.asyncio
    async def test_health_check_with_missing_company_name(self, mock_config):
        """Test highlight_health_check handles missing company name gracefully."""
        mock_client = AsyncMock()
        mock_client.get_company.return_value = {
            "id": 5678,
            # name is missing
        }

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        data = json.loads(result[0].text)
        assert data["status"] == "healthy"
        assert data["company_name"] == "Unknown"
        assert data["company_id"] == 5678

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_generic_exception(self, mock_config):
        """Test highlight_health_check returns unhealthy status on generic exception."""
        mock_client = AsyncMock()
        mock_client.get_company.side_effect = Exception("Unexpected internal error")

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["status"] == "unhealthy"
        assert data["company_name"] is None
        assert "unexpected error" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_health_check_extracts_api_version_from_config(self):
        """Test highlight_health_check extracts api_version from configured base_url."""
        mock_client = AsyncMock()
        mock_client.get_company.return_value = {"id": 1234, "name": "Test"}

        # Use a different API version in the base_url
        mock_config = MagicMock()
        mock_config.base_url = "https://api.example.com/v3"

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        data = json.loads(result[0].text)
        assert data["status"] == "healthy"
        assert data["api_version"] == "v3"  # Should match the path from base_url

    @pytest.mark.asyncio
    async def test_health_check_api_version_in_unhealthy_response(self):
        """Test api_version is included in unhealthy response from configured base_url."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get_company.side_effect = httpx.ConnectError("Connection failed")

        mock_config = MagicMock()
        mock_config.base_url = "https://api.example.com/api/v2-beta"

        with (
            patch("cast_highlight_mcp.server.get_client", return_value=mock_client),
            patch("cast_highlight_mcp.server.get_config", return_value=mock_config),
        ):
            result = await call_tool("highlight_health_check", {})

        data = json.loads(result[0].text)
        assert data["status"] == "unhealthy"
        assert data["api_version"] == "v2-beta"  # Should still include version from config
