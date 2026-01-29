# CLAUDE.md - Highlight MCP Server

> MCP Server for CAST Highlight API Integration
> **Status**: Active | **Version**: 0.1.0

## Priority Legend

- **[P0]** CRITICAL - Must know before ANY task
- **[P1]** HIGH - Required for most development work
- **[P2]** MEDIUM - Important for specific features
- **[P3]** LOW - Reference information

---

## [P0] Project Overview

**cast-highlight-mcp** is a Python MCP (Model Context Protocol) server that provides AI agents with access to CAST Highlight's application portfolio analysis and software intelligence capabilities.

### What This Project Does

- Exposes CAST Highlight REST API as MCP tools
- Provides application portfolio analysis to AI agents
- Delivers technology insights and software health metrics
- Enables cloud readiness and green impact assessments

### Tech Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.10+ |
| Language | Python |
| Protocol | MCP SDK (mcp) |
| HTTP Client | httpx |
| Config | python-dotenv |
| Test | pytest, pytest-asyncio |
| Lint | ruff |

---

## [P0] Single-Path Workflows

### Setup

```bash
make setup          # Create venv, install deps, copy .env.example
```

### Build/Install

```bash
make install        # Install dependencies in virtual environment
```

### Test

```bash
make test           # Run all tests
make test-coverage  # Run tests with coverage report
```

### Run Development Server

```bash
make run            # Run MCP server
make dev            # Alias for run
```

### Lint and Format

```bash
make lint           # Check for linting issues
make lint-fix       # Fix linting issues
make format         # Format code with ruff
make quality        # Run all quality checks
```

### Test API Connection

```bash
make test-api       # Test API connection with current credentials
```

---

## [P1] Project Structure

```
cast-highlight-mcp/
├── CLAUDE.md              # This file - AI agent instructions
├── README.md              # Project overview and setup
├── Makefile               # Single-path build commands
├── pyproject.toml         # Python project configuration
├── .env.example           # Environment template
├── src/
│   └── cast_highlight_mcp/
│       ├── __init__.py    # Package init
│       ├── server.py      # MCP server implementation
│       ├── client.py      # CAST Highlight API client
│       └── config.py      # Configuration management
├── tests/                 # Test files
│   ├── test_client.py     # API client tests
│   ├── test_server.py     # Server tests
│   └── test_tools.py      # MCP tool tests
├── docs/                  # Documentation
│   ├── API.md             # CAST Highlight API reference
│   ├── TOOLS.md           # MCP tools documentation
│   ├── DEVELOPER.md       # Developer guide
│   ├── TOKEN-SETUP.md     # Token setup guide
│   └── images/            # Documentation images
└── scripts/               # Utility scripts
    └── test_api.py        # API connection test script
```

---

## [P1] MCP Development Patterns

### Tool Definition Pattern

```python
# In server.py
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="highlight_get_company",
            description="Get company details",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {
                        "type": "integer",
                        "description": "Company ID (optional, uses default if not provided)",
                    }
                },
            },
        ),
        # ... more tools
    ]
```

### API Client Pattern

```python
# src/cast_highlight_mcp/client.py
class HighlightClient:
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.base_url
        self._client: httpx.AsyncClient | None = None

    async def get_company(self, company_id: int | None = None) -> dict:
        cid = company_id or self.config.company_id
        return await self.get(f"/companies/{cid}")
```

### Server Handler Pattern

```python
# src/cast_highlight_mcp/server.py
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    api = get_client()

    if name == "highlight_get_company":
        result = await api.get_company(arguments.get("company_id"))
    # ... handle other tools

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

---

## [P1] CAST Highlight API Integration

### Authentication

CAST Highlight uses OAuth2 Bearer tokens. Configuration via environment:

```bash
HIGHLIGHT_BASE_URL="https://app.casthighlight.com/WS2"
HIGHLIGHT_ACCESS_TOKEN="your-bearer-token"
HIGHLIGHT_COMPANY_ID="your-company-id"
```

See [docs/TOKEN-SETUP.md](./docs/TOKEN-SETUP.md) for detailed token generation instructions.

### Key API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/companies/{id}` | Get company details |
| `/domains/{id}` | Get domain details |
| `/domains/{id}/applications` | List applications in domain |
| `/domains/{id}/applications/{id}` | Get application details |
| `/domains/{id}/applications/{id}/metrics` | Application health metrics |
| `/domains/{id}/technologies` | Technologies in domain |

### Rate Limiting

- Implement exponential backoff (TODO: Issue #2)
- Cache responses where appropriate (TODO: Issue #9)
- Respect API rate limits (check headers)

---

## [P2] Environment Configuration

### Required Environment Variables

```bash
# .env (never commit!)
HIGHLIGHT_BASE_URL=https://app.casthighlight.com/WS2
HIGHLIGHT_ACCESS_TOKEN=your-bearer-token
HIGHLIGHT_COMPANY_ID=your-company-id
```

### Optional Configuration

```bash
HIGHLIGHT_TIMEOUT=30    # API timeout in seconds (default: 30)
```

---

## [P2] Testing Strategy

### Unit Tests

Test individual tools and API client methods in isolation.

```bash
make test
```

### Test with Coverage

```bash
make test-coverage
```

### Test File Naming

- `test_*.py` - All test files

### Running Specific Tests

```bash
.venv/bin/pytest tests/test_client.py -v
.venv/bin/pytest tests/ -k "test_get_company"
```

---

## [P2] Available MCP Tools

| Tool | Description |
|------|-------------|
| `highlight_get_company` | Get company details |
| `highlight_list_domains` | List all domains for company |
| `highlight_get_domain` | Get domain details |
| `highlight_list_applications` | List applications in domain |
| `highlight_get_application` | Get application details |
| `highlight_get_metrics` | Get application health metrics |
| `highlight_get_technologies` | Get technology breakdown |
| `highlight_get_cloud_readiness` | Cloud migration assessment |
| `highlight_get_green_impact` | Environmental impact metrics |
| `highlight_get_cves` | CVE vulnerabilities |
| `highlight_get_third_parties` | Third-party components |
| `highlight_get_benchmark` | Global benchmark comparison |

---

## [P3] Documentation Links

- [README.md](./README.md) - Project overview
- [docs/API.md](./docs/API.md) - CAST Highlight API reference
- [docs/TOOLS.md](./docs/TOOLS.md) - MCP tools documentation
- [docs/DEVELOPER.md](./docs/DEVELOPER.md) - Developer guide
- [docs/TOKEN-SETUP.md](./docs/TOKEN-SETUP.md) - Token setup guide

### External Resources

- [MCP SDK Documentation](https://modelcontextprotocol.io/docs)
- [CAST Highlight API Docs](https://doc.casthighlight.com/)
- [Python httpx Docs](https://www.python-httpx.org/)

---

## Quick Reference

| Task | Command |
|------|---------|
| Setup | `make setup` |
| Install | `make install` |
| Test | `make test` |
| Run server | `make run` |
| Lint | `make lint` |
| Lint fix | `make lint-fix` |
| Format | `make format` |
| Quality | `make quality` |
| Clean | `make clean` |
| Help | `make help` |
