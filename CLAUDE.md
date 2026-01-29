# CLAUDE.md - Highlight MCP Server

> MCP Server for CAST Highlight API Integration
> **Status**: Initial Setup | **Version**: 0.1.0

## Priority Legend

- **[P0]** CRITICAL - Must know before ANY task
- **[P1]** HIGH - Required for most development work
- **[P2]** MEDIUM - Important for specific features
- **[P3]** LOW - Reference information

---

## [P0] Project Overview

**cast-highlight-mcp** is a TypeScript MCP (Model Context Protocol) server that provides AI agents with access to CAST Highlight's application portfolio analysis and software intelligence capabilities.

### What This Project Does

- Exposes CAST Highlight REST API as MCP tools
- Provides application portfolio analysis to AI agents
- Delivers technology insights and software health metrics
- Enables cloud readiness and green impact assessments

### Tech Stack

| Component | Technology |
|-----------|------------|
| Runtime | Node.js 20+ |
| Language | TypeScript 5.x |
| Protocol | MCP SDK (@modelcontextprotocol/sdk) |
| API Client | CAST Highlight REST API v3 |
| Build | tsup |
| Test | Vitest |
| Lint | ESLint + Prettier |

---

## [P0] Single-Path Workflows

### Build

```bash
make build
```

### Test

```bash
make test
```

### Run Development Server

```bash
make dev
```

### Lint and Format

```bash
make lint-fix    # Fix all linting issues
make format      # Format all code
make quality     # Run all quality checks
```

### Type Check

```bash
make typecheck
```

---

## [P1] Project Structure

```
cast-highlight-mcp/
├── CLAUDE.md           # This file - AI agent instructions
├── README.md           # Project overview and setup
├── Makefile            # Single-path build commands
├── package.json        # Node.js dependencies
├── tsconfig.json       # TypeScript configuration
├── src/
│   ├── index.ts        # MCP server entry point
│   ├── server.ts       # MCP server implementation
│   ├── tools/          # MCP tool definitions
│   │   └── index.ts    # Tool exports
│   ├── api/            # CAST Highlight API client
│   │   ├── client.ts   # API client class
│   │   └── types.ts    # API type definitions
│   └── utils/          # Utility functions
├── tests/              # Test files
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── docs/               # Documentation
│   ├── API.md          # API reference
│   ├── TOOLS.md        # MCP tools documentation
│   └── DEVELOPER.md    # Developer guide
├── scripts/            # Utility scripts
│   └── setup.sh        # Initial setup script
└── .claude-mpm/        # Claude MPM configuration
    └── memories/       # Project knowledge base
```

---

## [P1] MCP Development Patterns

### Tool Definition Pattern

```typescript
// src/tools/example-tool.ts
import { z } from "zod";

export const exampleTool = {
  name: "highlight_example",
  description: "Brief description of what this tool does",
  inputSchema: z.object({
    applicationId: z.string().describe("The application ID"),
    // ... other parameters
  }),
  handler: async (params: { applicationId: string }) => {
    // Implementation
    return { result: "data" };
  },
};
```

### API Client Pattern

```typescript
// src/api/client.ts
export class HighlightClient {
  constructor(private config: HighlightConfig) {}

  async getApplications(): Promise<Application[]> {
    // API call implementation
  }
}
```

### Server Registration Pattern

```typescript
// src/server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";

const server = new Server({
  name: "cast-highlight-mcp",
  version: "0.1.0",
});

// Register tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [/* tool definitions */],
}));
```

---

## [P1] CAST Highlight API Integration

### Authentication

CAST Highlight uses OAuth2 Bearer tokens. Configuration via environment:

```bash
HIGHLIGHT_DOMAIN="your-domain.casthighlight.com"
HIGHLIGHT_CLIENT_ID="your-client-id"
HIGHLIGHT_CLIENT_SECRET="your-client-secret"
```

### Key API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/domains` | List available domains |
| `/domains/{id}/applications` | Get applications in portfolio |
| `/applications/{id}` | Application details |
| `/applications/{id}/metrics` | Application health metrics |
| `/applications/{id}/technologies` | Technology breakdown |
| `/applications/{id}/cloudReadiness` | Cloud migration readiness |

### Rate Limiting

- Implement exponential backoff
- Cache responses where appropriate
- Respect API rate limits (check headers)

---

## [P2] Environment Configuration

### Required Environment Variables

```bash
# .env (never commit!)
HIGHLIGHT_DOMAIN=          # CAST Highlight domain
HIGHLIGHT_CLIENT_ID=       # OAuth2 client ID
HIGHLIGHT_CLIENT_SECRET=   # OAuth2 client secret
```

### Optional Configuration

```bash
HIGHLIGHT_TIMEOUT=30000    # API timeout in ms
HIGHLIGHT_CACHE_TTL=300    # Cache TTL in seconds
LOG_LEVEL=info             # Logging level
```

---

## [P2] Testing Strategy

### Unit Tests

Test individual tools and API client methods in isolation.

```bash
make test-unit
```

### Integration Tests

Test against CAST Highlight API (requires credentials).

```bash
make test-integration
```

### Test File Naming

- `*.test.ts` - Unit tests
- `*.integration.ts` - Integration tests

---

## [P2] MCP Tools to Implement

### Phase 1: Core Tools

1. **highlight_list_applications** - List all applications in portfolio
2. **highlight_get_application** - Get application details
3. **highlight_get_metrics** - Get application health metrics
4. **highlight_get_technologies** - Get technology breakdown

### Phase 2: Analysis Tools

5. **highlight_cloud_readiness** - Cloud migration assessment
6. **highlight_green_impact** - Environmental impact metrics
7. **highlight_software_health** - Overall health score
8. **highlight_technical_debt** - Technical debt analysis

### Phase 3: Advanced Tools

9. **highlight_compare_applications** - Compare multiple apps
10. **highlight_trend_analysis** - Historical trend data
11. **highlight_recommendations** - AI-generated recommendations

---

## [P3] Documentation Links

- [README.md](./README.md) - Project overview
- [docs/API.md](./docs/API.md) - API reference
- [docs/TOOLS.md](./docs/TOOLS.md) - MCP tools documentation
- [docs/DEVELOPER.md](./docs/DEVELOPER.md) - Developer guide

### External Resources

- [MCP SDK Documentation](https://modelcontextprotocol.io/docs)
- [CAST Highlight API Docs](https://doc.casthighlight.com/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

## [P3] Memory System

Project knowledge is stored in `.claude-mpm/memories/`:

- `architecture.md` - Architecture decisions
- `api-patterns.md` - Discovered API patterns
- `troubleshooting.md` - Known issues and solutions

---

## Quick Reference

| Task | Command |
|------|---------|
| Build | `make build` |
| Test | `make test` |
| Dev server | `make dev` |
| Lint fix | `make lint-fix` |
| Type check | `make typecheck` |
| All quality | `make quality` |
| Clean | `make clean` |
