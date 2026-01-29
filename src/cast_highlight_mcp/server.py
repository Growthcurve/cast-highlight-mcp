"""CAST Highlight MCP Server."""

import asyncio
import json
from contextlib import AsyncExitStack

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import HighlightClient
from .config import load_config

# Initialize server
server = Server("cast-highlight-mcp")

# Client instance managed by lifecycle
_client: HighlightClient | None = None


def get_client() -> HighlightClient:
    """Get the managed client instance.

    Returns:
        The HighlightClient instance.

    Raises:
        RuntimeError: If called before client is initialized.
    """
    if _client is None:
        raise RuntimeError("Client not initialized. Server must be started with run_server().")
    return _client


# Define tools
TOOLS = [
    Tool(
        name="highlight_get_company",
        description="Get company details including domain count, application count, and status",
        inputSchema={
            "type": "object",
            "properties": {
                "company_id": {
                    "type": "integer",
                    "description": "Company ID (optional, uses default from config)",
                }
            },
        },
    ),
    Tool(
        name="highlight_list_domains",
        description="List all domains/portfolios for the company",
        inputSchema={
            "type": "object",
            "properties": {
                "company_id": {
                    "type": "integer",
                    "description": "Company ID (optional, uses default from config)",
                }
            },
        },
    ),
    Tool(
        name="highlight_get_domain",
        description="Get details for a specific domain/portfolio",
        inputSchema={
            "type": "object",
            "properties": {
                "domain_id": {"type": "integer", "description": "Domain ID"},
            },
            "required": ["domain_id"],
        },
    ),
    Tool(
        name="highlight_list_applications",
        description="List all applications in a domain with their health metrics",
        inputSchema={
            "type": "object",
            "properties": {
                "domain_id": {"type": "integer", "description": "Domain ID"},
            },
            "required": ["domain_id"],
        },
    ),
    Tool(
        name="highlight_get_application",
        description="Get detailed information about a specific application",
        inputSchema={
            "type": "object",
            "properties": {
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["application_id"],
        },
    ),
    Tool(
        name="highlight_get_metrics",
        description="Get health metrics for an application (software health, agility, elegance, resiliency)",
        inputSchema={
            "type": "object",
            "properties": {
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["application_id"],
        },
    ),
    Tool(
        name="highlight_get_technologies",
        description="Get technology breakdown for an application (languages, frameworks, libraries)",
        inputSchema={
            "type": "object",
            "properties": {
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["application_id"],
        },
    ),
    Tool(
        name="highlight_get_cloud_readiness",
        description="Get cloud migration readiness assessment for an application",
        inputSchema={
            "type": "object",
            "properties": {
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["application_id"],
        },
    ),
    Tool(
        name="highlight_get_green_impact",
        description="Get environmental/green impact metrics for an application",
        inputSchema={
            "type": "object",
            "properties": {
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["application_id"],
        },
    ),
    Tool(
        name="highlight_get_cves",
        description="Get CVE vulnerabilities affecting an application's dependencies",
        inputSchema={
            "type": "object",
            "properties": {
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["application_id"],
        },
    ),
    Tool(
        name="highlight_get_third_parties",
        description="Get third-party/open-source components used by an application",
        inputSchema={
            "type": "object",
            "properties": {
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["application_id"],
        },
    ),
    Tool(
        name="highlight_get_benchmark",
        description="Get benchmark statistics comparing against all CAST Highlight applications globally",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    api = get_client()

    try:
        if name == "highlight_get_company":
            result = await api.get_company(arguments.get("company_id"))
        elif name == "highlight_list_domains":
            result = await api.list_domains(arguments.get("company_id"))
        elif name == "highlight_get_domain":
            result = await api.get_domain(arguments["domain_id"])
        elif name == "highlight_list_applications":
            result = await api.get_domain_applications(arguments["domain_id"])
        elif name == "highlight_get_application":
            result = await api.get_application(arguments["application_id"])
        elif name == "highlight_get_metrics":
            result = await api.get_application_metrics(arguments["application_id"])
        elif name == "highlight_get_technologies":
            result = await api.get_application_technologies(arguments["application_id"])
        elif name == "highlight_get_cloud_readiness":
            result = await api.get_application_cloud_readiness(arguments["application_id"])
        elif name == "highlight_get_green_impact":
            result = await api.get_application_green_impact(arguments["application_id"])
        elif name == "highlight_get_cves":
            result = await api.get_application_cves(arguments["application_id"])
        elif name == "highlight_get_third_parties":
            result = await api.get_application_third_parties(arguments["application_id"])
        elif name == "highlight_get_benchmark":
            result = await api.get_benchmark()
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def main():
    """Run the MCP server."""

    async def run():
        global _client

        async with AsyncExitStack() as stack:
            # Initialize client with proper lifecycle management
            config = load_config()
            _client = await stack.enter_async_context(HighlightClient(config))

            # Run the MCP server
            read_stream, write_stream = await stack.enter_async_context(stdio_server())
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
