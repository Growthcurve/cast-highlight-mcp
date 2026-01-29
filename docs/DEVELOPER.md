# Developer Guide

This guide covers development practices for contributing to the Highlight MCP Server.

## Getting Started

### Prerequisites

- Node.js 20 or later
- npm 10 or later
- Git

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/highlight-mcp.git
cd highlight-mcp

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

### Running Locally

```bash
# Development mode with hot reload
make dev

# Or using npm
npm run dev
```

## Project Structure

```
src/
├── index.ts          # Entry point
├── server.ts         # MCP server setup
├── config.ts         # Configuration management
├── api/
│   ├── client.ts     # CAST Highlight API client
│   └── types.ts      # Type definitions
├── tools/
│   ├── index.ts      # Tool registry
│   ├── list-applications.ts
│   └── get-application.ts
└── utils/
    └── logger.ts     # Logging utility
```

## Adding New Tools

### 1. Create Tool File

Create a new file in `src/tools/`:

```typescript
// src/tools/my-new-tool.ts
import { z } from "zod";
import type { HighlightConfig } from "../config.js";
import { HighlightClient } from "../api/client.js";

export const myNewTool = {
  name: "highlight_my_new_tool",
  description: "What this tool does",
  inputSchema: {
    type: "object" as const,
    properties: {
      param1: {
        type: "string",
        description: "Parameter description",
      },
    },
    required: ["param1"],
  },
};

const inputSchema = z.object({
  param1: z.string(),
});

export async function handleMyNewTool(
  args: Record<string, unknown>,
  config: HighlightConfig
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const parsed = inputSchema.parse(args);
  const client = new HighlightClient(config);

  // Implementation here

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
}
```

### 2. Register Tool

Update `src/tools/index.ts`:

```typescript
import { myNewTool, handleMyNewTool } from "./my-new-tool.js";

export const tools = [
  // ... existing tools
  myNewTool,
];

const handlers: Record<string, ToolHandler> = {
  // ... existing handlers
  highlight_my_new_tool: handleMyNewTool,
};
```

### 3. Add Tests

Create `tests/unit/my-new-tool.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { myNewTool } from "../../src/tools/my-new-tool.js";

describe("myNewTool", () => {
  it("should have correct name", () => {
    expect(myNewTool.name).toBe("highlight_my_new_tool");
  });

  // Add more tests
});
```

### 4. Update Documentation

Update `docs/TOOLS.md` with the new tool documentation.

## Testing

### Unit Tests

```bash
make test-unit
```

### Integration Tests

```bash
# Requires valid CAST Highlight credentials
make test-integration
```

### Coverage

```bash
make test-coverage
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

### Type Checking

```bash
make typecheck
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

## Building

```bash
make build
```

Output is generated in `dist/` directory.

## Debugging

### Enable Debug Logging

```bash
LOG_LEVEL=debug make dev
```

### Test MCP Server

Use the MCP Inspector tool:

```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

## API Client Development

When adding new API methods to `src/api/client.ts`:

1. Add return types to `src/api/types.ts`
2. Implement the method using the `request` helper
3. Add error handling
4. Add tests

## Release Process

1. Update version in `package.json`
2. Update CHANGELOG.md
3. Run `make quality`
4. Create release commit
5. Tag the release
6. Push to main
