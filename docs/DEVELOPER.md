# Developer Guide

This guide covers development practices for contributing to the Highlight MCP Server.

## Getting Started

### Prerequisites

- Python 3.10 or later
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/Growthcurve/cast-highlight-mcp.git
cd cast-highlight-mcp

# Run setup (creates venv, installs deps, copies .env.example)
make setup

# Edit .env with your credentials
```

Or manually:

```bash
# Create virtual environment
python3 -m venv .venv

# Install dependencies
.venv/bin/pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

### Running Locally

```bash
# Run the MCP server
make run

# Or directly
.venv/bin/cast-highlight-mcp
```

## Project Structure

```
src/cast_highlight_mcp/
├── __init__.py       # Package init
├── server.py         # MCP server setup and tool handlers
├── client.py         # CAST Highlight API client
└── config.py         # Configuration management
```

## Adding New Tools

### 1. Add Tool Definition

In `src/cast_highlight_mcp/server.py`, add to the `list_tools()` function:

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ... existing tools
        Tool(
            name="highlight_my_new_tool",
            description="What this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Parameter description",
                    },
                },
                "required": ["param1"],
            },
        ),
    ]
```

### 2. Add Tool Handler

In `src/cast_highlight_mcp/server.py`, add to the `call_tool()` function:

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    api = get_client()

    try:
        # ... existing handlers
        elif name == "highlight_my_new_tool":
            result = await api.my_new_method(arguments["param1"])

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]
```

### 3. Add API Client Method (if needed)

In `src/cast_highlight_mcp/client.py`:

```python
class HighlightClient:
    # ... existing methods

    async def my_new_method(self, param1: str) -> dict:
        """Description of what this method does."""
        return await self.get(f"/some/endpoint/{param1}")
```

### 4. Add Tests

Create or update tests in `tests/`:

```python
# tests/test_tools.py
import pytest
from cast_highlight_mcp.server import list_tools

@pytest.mark.asyncio
async def test_my_new_tool_definition():
    tools = await list_tools()
    tool_names = [t.name for t in tools]
    assert "highlight_my_new_tool" in tool_names
```

```python
# tests/test_client.py
import pytest
from cast_highlight_mcp.client import HighlightClient

@pytest.mark.asyncio
async def test_my_new_method(mock_client):
    # Test implementation
    pass
```

### 5. Update Documentation

Update `docs/TOOLS.md` with the new tool documentation.

## Testing

### Run All Tests

```bash
make test
```

### Run Tests with Coverage

```bash
make test-coverage
```

### Run Specific Tests

```bash
# Run a specific test file
.venv/bin/pytest tests/test_client.py -v

# Run tests matching a pattern
.venv/bin/pytest tests/ -k "test_get_company" -v

# Run with verbose output
.venv/bin/pytest tests/ -v --tb=short
```

### Test API Connection

```bash
make test-api
```

## Code Quality

### Linting

```bash
# Check for issues
make lint

# Auto-fix issues
make lint-fix
```

### Formatting

```bash
make format
```

### All Quality Checks

```bash
make quality
```

## Commit Guidelines

- Use conventional commits format
- Include tests for new features
- Run `make quality` before committing

### Commit Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Debugging

### Enable Debug Logging

```python
# In your code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test MCP Server

Use the MCP Inspector tool:

```bash
npx @modelcontextprotocol/inspector .venv/bin/cast-highlight-mcp
```

### Interactive Testing

```python
# Start Python REPL with the client
.venv/bin/python

>>> import asyncio
>>> from cast_highlight_mcp.client import HighlightClient
>>> from cast_highlight_mcp.config import load_config
>>>
>>> config = load_config()
>>> client = HighlightClient(config)
>>>
>>> # Test a method
>>> result = asyncio.run(client.get_company())
>>> print(result)
```

## API Client Development

When adding new API methods to `src/cast_highlight_mcp/client.py`:

1. Add the method with proper type hints
2. Use the existing `get()`, `post()`, etc. helper methods
3. Add error handling as appropriate
4. Add tests in `tests/test_client.py`

### Example API Method

```python
async def get_something(self, domain_id: int, app_id: int) -> dict:
    """Get something for an application.

    Args:
        domain_id: The domain ID
        app_id: The application ID

    Returns:
        Dict containing something data
    """
    return await self.get(f"/domains/{domain_id}/applications/{app_id}/something")
```

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md (if exists)
3. Run `make quality`
4. Create release commit
5. Tag the release: `git tag v0.x.x`
6. Push to main: `git push origin main --tags`

## Common Issues

### Import Errors

Make sure you're using the virtual environment:

```bash
source .venv/bin/activate
# or use .venv/bin/python directly
```

### API Authentication Errors

1. Check `.env` file has correct credentials
2. Verify token hasn't expired
3. Test with `make test-api`

### Test Failures

1. Ensure dependencies are installed: `make install`
2. Check for syntax errors: `make lint`
3. Run specific failing test with `-v` flag for details
