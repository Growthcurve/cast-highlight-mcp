# CAST Highlight MCP Server

An MCP (Model Context Protocol) server that provides AI agents with access to CAST Highlight's application portfolio analysis and software intelligence capabilities.

## Overview

This MCP server wraps the CAST Highlight REST API, enabling AI agents to:

- Query application portfolios and domains
- Analyze technology stacks
- Assess cloud readiness
- Evaluate software health metrics
- Review CVE vulnerabilities
- Analyze green/environmental impact
- Access third-party component information
- Compare against global benchmarks

## Quick Start

### Prerequisites

- Python 3.10 or later
- CAST Highlight account with API access
- API access token

### Installation

#### From GitHub

```bash
pip install git+https://github.com/Growthcurve/cast-highlight-mcp.git
```

#### From source

```bash
git clone https://github.com/Growthcurve/cast-highlight-mcp.git
cd cast-highlight-mcp
pip install -e .
```

### Configuration

Set the following environment variables:

```bash
# Required
HIGHLIGHT_BASE_URL=https://rpa.casthighlight.com/WS2
HIGHLIGHT_ACCESS_TOKEN=your-access-token
HIGHLIGHT_COMPANY_ID=your-company-id

# Optional
HIGHLIGHT_TIMEOUT=30  # API timeout in seconds (default: 30)
```

You can also create a `.env` file in your project directory:

```bash
HIGHLIGHT_BASE_URL=https://rpa.casthighlight.com/WS2
HIGHLIGHT_ACCESS_TOKEN=your-access-token
HIGHLIGHT_COMPANY_ID=12345
```

### Running

```bash
# Run the MCP server
cast-highlight-mcp
```

## MCP Integration

### Claude Desktop

Add to your Claude Desktop configuration file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "highlight": {
      "command": "cast-highlight-mcp",
      "env": {
        "HIGHLIGHT_BASE_URL": "https://rpa.casthighlight.com/WS2",
        "HIGHLIGHT_ACCESS_TOKEN": "your-access-token",
        "HIGHLIGHT_COMPANY_ID": "12345"
      }
    }
  }
}
```

If installed in a virtual environment or using uv, specify the full path:

```json
{
  "mcpServers": {
    "highlight": {
      "command": "/path/to/venv/bin/cast-highlight-mcp",
      "env": {
        "HIGHLIGHT_BASE_URL": "https://rpa.casthighlight.com/WS2",
        "HIGHLIGHT_ACCESS_TOKEN": "your-access-token",
        "HIGHLIGHT_COMPANY_ID": "12345"
      }
    }
  }
}
```

Or using uv to run directly:

```json
{
  "mcpServers": {
    "highlight": {
      "command": "uv",
      "args": ["run", "cast-highlight-mcp"],
      "env": {
        "HIGHLIGHT_BASE_URL": "https://rpa.casthighlight.com/WS2",
        "HIGHLIGHT_ACCESS_TOKEN": "your-access-token",
        "HIGHLIGHT_COMPANY_ID": "12345"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `highlight_get_company` | Get company details including domain count, application count, and status |
| `highlight_list_domains` | List all domains/portfolios for the company |
| `highlight_get_domain` | Get details for a specific domain/portfolio |
| `highlight_list_applications` | List all applications in a domain with their health metrics |
| `highlight_get_application` | Get detailed information about a specific application |
| `highlight_get_metrics` | Get health metrics for an application (software health, agility, elegance, resiliency) |
| `highlight_get_technologies` | Get technology breakdown for an application (languages, frameworks, libraries) |
| `highlight_get_cloud_readiness` | Get cloud migration readiness assessment for an application |
| `highlight_get_green_impact` | Get environmental/green impact metrics for an application |
| `highlight_get_cves` | Get CVE vulnerabilities affecting an application's dependencies |
| `highlight_get_third_parties` | Get third-party/open-source components used by an application |
| `highlight_get_benchmark` | Get benchmark statistics comparing against all CAST Highlight applications globally |

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/Growthcurve/cast-highlight-mcp.git
cd cast-highlight-mcp

# Install with dev dependencies
pip install -e ".[dev]"

# Or with uv
uv pip install -e ".[dev]"
```

### Commands

```bash
# Run tests
pytest

# Run linter
ruff check .

# Format code
ruff format .
```

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol SDK
- `httpx>=0.27.0` - Async HTTP client
- `python-dotenv>=1.0.0` - Environment variable management

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request
