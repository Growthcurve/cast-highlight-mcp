"""CAST Highlight MCP Server."""

import asyncio
import json
from contextlib import AsyncExitStack

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import HighlightClient
from .config import Config, load_config
from .observability import (
    configure_logging,
    get_logger,
    get_metrics_collector,
    request_context,
)
from .validation import (
    ValidationError,
    validate_application_args,
    validate_get_company_args,
    validate_get_domain_args,
    validate_list_applications_args,
    validate_list_domains_args,
)

# Initialize server
server = Server("cast-highlight-mcp")

# Module-level logger (configured in main())
logger = get_logger(__name__)

# Client instance managed by lifecycle
_client: HighlightClient | None = None
_config: Config | None = None


def _extract_api_version(base_url: str) -> str:
    """Extract API version identifier from the base URL.

    Parses the base_url path to find version identifiers like "WS2", "v1", "v2", etc.
    Falls back to "unknown" if the last path segment doesn't match a version pattern.

    Args:
        base_url: The configured API base URL (e.g., "https://app.casthighlight.com/WS2")

    Returns:
        The API version string extracted from the URL path, or "unknown" if not found.
    """
    import re
    from urllib.parse import urlparse

    # Pattern to match version identifiers like v1, v2, WS2, v3-beta, WS1, etc.
    # Case-insensitive to handle V1, ws2, etc.
    version_pattern = re.compile(r"^(v\d+|WS\d+|v\d+-\w+)$", re.IGNORECASE)

    parsed = urlparse(base_url)
    # Get the last path segment (e.g., "/WS2" -> "WS2", "/api/v2" -> "v2")
    path_parts = [p for p in parsed.path.split("/") if p]
    if path_parts:
        last_segment = path_parts[-1]
        # Only return if it matches a version pattern
        if version_pattern.match(last_segment):
            return last_segment
    return "unknown"


def get_client() -> HighlightClient:
    """Get the managed client instance.

    Returns:
        The HighlightClient instance.

    Raises:
        RuntimeError: If called before client is initialized.
    """
    if _client is None:
        raise RuntimeError("Client not initialized. Server lifecycle not started.")
    return _client


def get_config() -> Config:
    """Get the loaded configuration.

    Returns:
        The Config instance.

    Raises:
        RuntimeError: If called before config is loaded.
    """
    if _config is None:
        raise RuntimeError("Config not loaded. Server lifecycle not started.")
    return _config


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
                "domain_id": {
                    "type": "integer",
                    "description": "Domain ID containing the application",
                },
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["domain_id", "application_id"],
        },
    ),
    Tool(
        name="highlight_get_metrics",
        description="Get health metrics for an application (software health, agility, elegance, resiliency)",
        inputSchema={
            "type": "object",
            "properties": {
                "domain_id": {
                    "type": "integer",
                    "description": "Domain ID containing the application",
                },
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["domain_id", "application_id"],
        },
    ),
    Tool(
        name="highlight_get_components",
        description="Get third-party components for an application including technologies, versions, licenses, and CVE data",
        inputSchema={
            "type": "object",
            "properties": {
                "domain_id": {
                    "type": "integer",
                    "description": "Domain ID containing the application",
                },
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["domain_id", "application_id"],
        },
    ),
    Tool(
        name="highlight_get_cloud_readiness",
        description="Get cloud migration readiness assessment for an application",
        inputSchema={
            "type": "object",
            "properties": {
                "domain_id": {
                    "type": "integer",
                    "description": "Domain ID containing the application",
                },
                "application_id": {"type": "integer", "description": "Application ID"},
            },
            "required": ["domain_id", "application_id"],
        },
    ),
    Tool(
        name="highlight_get_cves",
        description="Get all CVE vulnerabilities across applications in a domain",
        inputSchema={
            "type": "object",
            "properties": {
                "domain_id": {
                    "type": "integer",
                    "description": "Domain ID to retrieve CVEs for",
                },
            },
            "required": ["domain_id"],
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
    Tool(
        name="highlight_health_check",
        description="Check the health of the CAST Highlight API connection. Validates credentials, API connectivity, and returns status information.",
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
    if isinstance(exception, ValidationError):
        return "validation"
    elif isinstance(exception, httpx.HTTPStatusError):
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


def _sanitize_error_message(exception: Exception) -> str:
    """Create a sanitized error message safe for client exposure.

    Prevents information leakage by returning generic messages
    that don't expose sensitive details like URLs, headers, or
    internal system information.

    Args:
        exception: The exception to sanitize

    Returns:
        A sanitized error message safe for client exposure
    """
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        # Only expose status code, not the full response or URL
        if status == 401:
            return "API error: Authentication failed (401)"
        elif status == 403:
            return "API error: Access forbidden (403)"
        elif status == 404:
            return "API error: Resource not found (404)"
        elif status == 429:
            return "API error: Rate limit exceeded (429)"
        elif 400 <= status < 500:
            return f"API error: Client error ({status})"
        elif 500 <= status < 600:
            return f"API error: Server error ({status})"
        return f"API error: HTTP {status}"
    elif isinstance(exception, httpx.TimeoutException):
        return "Network error: Request timed out"
    elif isinstance(exception, httpx.ConnectError):
        return "Network error: Unable to connect to CAST Highlight API"
    elif isinstance(exception, httpx.RequestError):
        return "Network error: Failed to communicate with CAST Highlight API"
    elif isinstance(exception, ValueError):
        # ValueError may contain user input, so sanitize it
        return "Validation error: Invalid argument value"
    elif isinstance(exception, ValidationError):
        # ValidationError contains field name and message which are safe to expose
        return f"Validation error: {exception.message} (field: {exception.field})"
    elif isinstance(exception, KeyError):
        # KeyError contains the missing key name which is safe to expose
        key = str(exception).strip("'\"")
        return f"Missing required argument: {key}"
    elif isinstance(exception, RuntimeError):
        # RuntimeError from get_client() is safe - it's our own message
        if "not initialized" in str(exception).lower():
            return "Server error: Service not ready"
        return "An unexpected error occurred"
    # Generic fallback - never expose raw exception messages
    return "An unexpected error occurred"


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
                validated = validate_get_company_args(arguments)
                result = await api.get_company(validated.company_id)
            elif name == "highlight_list_domains":
                validated = validate_list_domains_args(arguments)
                result = await api.list_domains(validated.company_id)
            elif name == "highlight_get_domain":
                validated = validate_get_domain_args(arguments)
                result = await api.get_domain(validated.domain_id)
            elif name == "highlight_list_applications":
                validated = validate_list_applications_args(arguments)
                result = await api.get_domain_applications(validated.domain_id)
            elif name == "highlight_get_application":
                validated = validate_application_args(arguments)
                result = await api.get_application(validated.domain_id, validated.application_id)
            elif name == "highlight_get_metrics":
                validated = validate_application_args(arguments)
                result = await api.get_application_metrics(
                    validated.domain_id, validated.application_id
                )
            elif name == "highlight_get_components":
                validated = validate_application_args(arguments)
                result = await api.get_application_components(
                    validated.domain_id, validated.application_id
                )
            elif name == "highlight_get_cloud_readiness":
                validated = validate_application_args(arguments)
                result = await api.get_application_cloud_readiness(
                    validated.domain_id, validated.application_id
                )
            elif name == "highlight_get_cves":
                validated = validate_get_domain_args(arguments)
                result = await api.get_domain_cves(validated.domain_id)
            elif name == "highlight_get_benchmark":
                result = await api.get_benchmark()
            elif name == "highlight_health_check":
                # Health check: verify API connectivity by calling get_company
                # Extract API version from configured base_url for accurate reporting
                config = get_config()
                api_version = _extract_api_version(config.base_url)
                try:
                    company = await api.get_company()
                    result = {
                        "status": "healthy",
                        "company_name": company.get("name", "Unknown"),
                        "company_id": company.get("id"),
                        "api_version": api_version,
                        "message": "Successfully connected to CAST Highlight API",
                    }
                except Exception as health_error:
                    # Health check exceptions are caught here intentionally.
                    # Returning "unhealthy" status IS a successful tool execution - the tool
                    # correctly reported the health state. This is different from the tool
                    # itself failing. The outer call_tool metrics will show success=True
                    # because the tool executed its contract correctly.
                    #
                    # However, we log at WARNING level and include error_type in the response
                    # so that monitoring/observability systems can detect API connectivity
                    # issues even though the tool call itself succeeded.
                    error_type = _classify_error(health_error)
                    logger.warning(
                        "Health check returned unhealthy status",
                        extra={
                            "context": {
                                "tool_name": name,
                                "request_id": ctx.request_id,
                                "error_type": error_type,
                                "health_status": "unhealthy",
                            }
                        },
                    )
                    result = {
                        "status": "unhealthy",
                        "company_name": None,
                        "company_id": None,
                        "api_version": api_version,
                        "error_type": error_type,
                        "message": _sanitize_error_message(health_error),
                    }
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

            # Return sanitized error message to prevent information leakage
            sanitized_message = _sanitize_error_message(e)
            return [TextContent(type="text", text=sanitized_message)]


def main():
    """Run the MCP server."""
    # Configure logging first, before any log statements
    configure_logging()

    async def run():
        global _client, _config

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
                _config = load_config()
                _client = await stack.enter_async_context(HighlightClient(_config))

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
