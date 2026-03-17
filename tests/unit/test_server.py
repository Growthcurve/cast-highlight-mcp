"""Tests for MCP server."""

import pytest

from cast_highlight_mcp.server import TOOLS, list_tools


class TestToolDefinitions:
    """Tests for MCP tool definitions."""

    def test_tools_not_empty(self):
        """Test that tools are defined."""
        assert len(TOOLS) > 0

    def test_all_tools_have_required_fields(self):
        """Test all tools have name, description, and inputSchema."""
        for tool in TOOLS:
            assert tool.name, "Tool missing name"
            assert tool.description, f"Tool {tool.name} missing description"
            assert tool.inputSchema, f"Tool {tool.name} missing inputSchema"

    def test_tool_names_are_prefixed(self):
        """Test all tool names start with highlight_."""
        for tool in TOOLS:
            assert tool.name.startswith("highlight_"), (
                f"Tool {tool.name} should start with 'highlight_'"
            )

    def test_tool_names_are_unique(self):
        """Test all tool names are unique."""
        names = [tool.name for tool in TOOLS]
        assert len(names) == len(set(names)), "Duplicate tool names found"

    def test_expected_tools_exist(self):
        """Test that expected core tools are defined."""
        tool_names = {tool.name for tool in TOOLS}
        expected = {
            "highlight_get_company",
            "highlight_list_domains",
            "highlight_get_domain",
            "highlight_list_applications",
            "highlight_get_application",
            "highlight_get_metrics",
            "highlight_get_components",
            "highlight_get_cloud_readiness",
            "highlight_get_cves",
            "highlight_get_benchmark",
            "highlight_health_check",
        }
        missing = expected - tool_names
        assert not missing, f"Missing expected tools: {missing}"


class TestToolSchemas:
    """Tests for tool input schemas."""

    def test_company_tools_have_optional_company_id(self):
        """Test company-related tools have optional company_id."""
        company_tools = ["highlight_get_company", "highlight_list_domains"]
        for tool in TOOLS:
            if tool.name in company_tools:
                schema = tool.inputSchema
                assert "company_id" in schema.get("properties", {}), (
                    f"{tool.name} should have company_id property"
                )
                # company_id should be optional (not in required)
                required = schema.get("required", [])
                assert "company_id" not in required, f"{tool.name} company_id should be optional"

    def test_application_tools_require_domain_and_application_id(self):
        """Test application tools require both domain_id and application_id."""
        app_tools = [
            "highlight_get_application",
            "highlight_get_metrics",
            "highlight_get_components",
            "highlight_get_cloud_readiness",
        ]
        for tool in TOOLS:
            if tool.name in app_tools:
                schema = tool.inputSchema
                required = schema.get("required", [])
                assert "domain_id" in required, f"{tool.name} should require domain_id"
                assert "application_id" in required, f"{tool.name} should require application_id"

    def test_cves_tool_requires_only_domain_id(self):
        """Test CVE tool requires only domain_id (domain-level endpoint)."""
        for tool in TOOLS:
            if tool.name == "highlight_get_cves":
                schema = tool.inputSchema
                required = schema.get("required", [])
                assert "domain_id" in required
                assert "application_id" not in required

    def test_domain_tools_require_domain_id(self):
        """Test domain tools require domain_id."""
        domain_tools = ["highlight_get_domain", "highlight_list_applications"]
        for tool in TOOLS:
            if tool.name in domain_tools:
                schema = tool.inputSchema
                required = schema.get("required", [])
                assert "domain_id" in required, f"{tool.name} should require domain_id"


class TestListTools:
    """Tests for list_tools handler."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self):
        """Test list_tools returns all defined tools."""
        result = await list_tools()
        assert result == TOOLS
        assert len(result) == len(TOOLS)
