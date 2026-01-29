# Highlight MCP Server

An MCP (Model Context Protocol) server that provides AI agents with access to CAST Highlight's application portfolio analysis and software intelligence capabilities.

## Overview

This MCP server wraps the CAST Highlight REST API, enabling AI agents to:

- Query application portfolios
- Analyze technology stacks
- Assess cloud readiness
- Evaluate software health metrics
- Identify technical debt
- Generate insights and recommendations

## Quick Start

### Prerequisites

- Node.js 20 or later
- CAST Highlight account with API access
- API credentials (client ID and secret)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/highlight-mcp.git
cd highlight-mcp

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your CAST Highlight credentials

# Build the project
make build
```

### Configuration

Create a `.env` file with your CAST Highlight credentials:

```bash
HIGHLIGHT_DOMAIN=your-domain.casthighlight.com
HIGHLIGHT_CLIENT_ID=your-client-id
HIGHLIGHT_CLIENT_SECRET=your-client-secret
```

### Running

```bash
# Development mode
make dev

# Production
make build && node dist/index.js
```

## MCP Integration

### Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "highlight": {
      "command": "node",
      "args": ["/path/to/highlight-mcp/dist/index.js"],
      "env": {
        "HIGHLIGHT_DOMAIN": "your-domain.casthighlight.com",
        "HIGHLIGHT_CLIENT_ID": "your-client-id",
        "HIGHLIGHT_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

### Programmatic Usage

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";

const client = new Client({
  name: "my-app",
  version: "1.0.0",
});

// Connect to the Highlight MCP server
await client.connect(transport);

// Use tools
const result = await client.callTool({
  name: "highlight_list_applications",
  arguments: { domainId: "your-domain-id" },
});
```

## Available Tools

| Tool | Description |
|------|-------------|
| `highlight_list_applications` | List all applications in a portfolio |
| `highlight_get_application` | Get detailed application information |
| `highlight_get_metrics` | Retrieve application health metrics |
| `highlight_get_technologies` | Get technology breakdown for an application |
| `highlight_cloud_readiness` | Assess cloud migration readiness |
| `highlight_software_health` | Get overall software health score |

See [docs/TOOLS.md](docs/TOOLS.md) for complete tool documentation.

## Development

```bash
# Run tests
make test

# Run linter
make lint-fix

# Type check
make typecheck

# All quality checks
make quality
```

See [CLAUDE.md](CLAUDE.md) for AI agent development instructions.

## Documentation

- [CLAUDE.md](CLAUDE.md) - AI agent instructions
- [docs/API.md](docs/API.md) - API reference
- [docs/TOOLS.md](docs/TOOLS.md) - MCP tools documentation
- [docs/DEVELOPER.md](docs/DEVELOPER.md) - Developer guide

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make quality` to ensure code quality
5. Submit a pull request

See [docs/DEVELOPER.md](docs/DEVELOPER.md) for detailed contribution guidelines.
