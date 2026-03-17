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
| Lint | ruff, pre-commit |

---

## [P0] Single-Path Workflows

### Setup

```bash
make setup          # Create venv, install deps, install pre-commit hooks
make hooks          # Install pre-commit hooks only (runs on every commit)
```

**Note**: If commits fail with `pre-commit not found`, reinstall hooks:
```bash
source .venv/bin/activate && pre-commit install
```
This can happen after git worktree cleanup when hooks point to deleted paths.

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

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/companies/{id}` | GET | Get company details |
| `/domains/{id}` | GET | Get domain details |
| `/domains/{id}/applications` | GET | List applications in domain |
| `/domains/{id}/applications/{id}` | GET | Get application details |
| `/domains/{id}/applications/{id}/results` | GET | Application results/metrics |
| `/domains/{id}/applications/{id}/components` | GET | Components and technologies |
| `/domains/{id}/applications/{id}/containerization` | GET | Cloud readiness |
| `/domains/{id}/vulnerabilities` | POST | Domain-wide CVEs |

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

## [P1] Augment Code Review Workflow

This repository uses [Augment Code](https://www.augmentcode.com/) for automated PR reviews.

### How It Works

1. **Auto-review on first commit**: Augment automatically reviews the first commit on any PR
2. **Eyes emoji (👀)**: Indicates Augment is currently reviewing - wait for it to complete
3. **Review comments**: Augment posts inline suggestions on specific lines
4. **Summary comment**: Posts a PR summary with "No suggestions" or "N suggestions posted"

### Checking Review Status

```bash
# Check for Augment reviews on a PR
gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews \
  --jq '.[] | select(.user.login | contains("augment")) | {state, body}'

# Check for inline suggestions
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments \
  --jq '.[] | select(.user.login | contains("augment")) | {path, line, body}'
```

### Triggering Re-review

After pushing fixes for Augment feedback, trigger a new review:

```bash
gh pr comment PR_NUMBER --body "auggie review"
```

**Note**: Only needed after subsequent commits. First commit is auto-reviewed.

### Workflow

1. Create PR → Augment auto-reviews (watch for 👀 emoji)
2. Check review: "No suggestions" = ready to merge
3. If suggestions posted:
   - Read inline comments
   - Fix issues
   - Push commits
   - Comment `auggie review` to re-trigger
   - Wait for "No suggestions"
4. Merge when Augment approves

### Best Practices

- **Don't merge until Augment reviews** - Always wait for the review to complete
- **Address all suggestions** - Fix issues or explain why not applicable
- **Create follow-up issues** - For valid feedback on already-merged PRs

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
| `highlight_get_components` | Get third-party components |
| `highlight_get_cloud_readiness` | Cloud migration assessment |
| `highlight_get_cves` | Domain-wide CVE vulnerabilities |
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
