"""CAST Highlight MCP Server."""

import asyncio
import json
from contextlib import AsyncExitStack

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import HighlightClient
from .config import load_config
from .observability import (
    configure_logging,
    get_logger,
    get_metrics_collector,
    request_context,
)

# Initialize server
server = Server("cast-highlight-mcp")

# Module-level logger (configured in main())
logger = get_logger(__name__)

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


def _classify_error(exception: Exception) -> str:
    """Classify an exception for metrics tracking.

    Args:
        exception: The exception to classify

    Returns:
        Error type string for metrics
    """
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        return f"http_{status}"
    elif isinstance(exception, httpx.TimeoutException):
        return "timeout"
    elif isinstance(exception, httpx.ConnectError):
        return "connection"
    elif isinstance(exception, ValueError):
        return "validation"
    elif isinstance(exception, KeyError):
        return "missing_argument"
    return "unknown"


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    api = get_client()
    metrics = get_metrics_collector()

    with request_context(tool_name=name) as ctx:
        # Log tool call start
        logger.info(
            "Tool call started",
            extra={"context": {"tool_name": name, "request_id": ctx.request_id}},
        )

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
                # Unknown tool - log warning and return error
                duration_ms = ctx.elapsed_ms()
                logger.warning(
                    "Unknown tool requested",
                    extra={
                        "context": {
                            "tool_name": name,
                            "request_id": ctx.request_id,
                            "duration_ms": round(duration_ms, 2),
                        }
                    },
                )
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            # Calculate duration and log success
            duration_ms = ctx.elapsed_ms()
            logger.info(
                "Tool call completed",
                extra={
                    "context": {
                        "tool_name": name,
                        "request_id": ctx.request_id,
                        "duration_ms": round(duration_ms, 2),
                        "success": True,
                    }
                },
            )

            # Record metrics
            metrics.record_tool_call(
                tool_name=name,
                duration_ms=duration_ms,
                success=True,
            )

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            # Calculate duration and classify error
            duration_ms = ctx.elapsed_ms()
            error_type = _classify_error(e)

            # Log failure
            logger.error(
                "Tool call failed",
                extra={
                    "context": {
                        "tool_name": name,
                        "request_id": ctx.request_id,
                        "duration_ms": round(duration_ms, 2),
                        "success": False,
                        "error_type": error_type,
                        "error_message": str(e),
                    }
                },
            )

            # Record metrics
            metrics.record_tool_call(
                tool_name=name,
                duration_ms=duration_ms,
                success=False,
                error_type=error_type,
            )

            return [TextContent(type="text", text=f"Error: {str(e)}")]


def main():
    """Run the MCP server."""
    # Configure logging first, before any log statements
    configure_logging()

    async def run():
        global _client

        # Log server starting
        logger.info(
            "Server starting",
            extra={
                "context": {
                    "server_name": "cast-highlight-mcp",
                }
            },
        )

        try:
            async with AsyncExitStack() as stack:
                # Initialize client with proper lifecycle management
                config = load_config()
                _client = await stack.enter_async_context(HighlightClient(config))

                # Log server ready
                logger.info(
                    "Server ready",
                    extra={
                        "context": {
                            "tools_count": len(TOOLS),
                        }
                    },
                )

                # Run the MCP server
                read_stream, write_stream = await stack.enter_async_context(stdio_server())
                await server.run(read_stream, write_stream, server.create_initialization_options())

        except Exception as e:
            logger.critical(
                "Server failed to start",
                extra={
                    "context": {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                },
                exc_info=True,
            )
            raise

        finally:
            logger.info("Server shutdown")

    asyncio.run(run())


if __name__ == "__main__":
    main()
