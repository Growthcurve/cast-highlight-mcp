# MCP Tools Documentation

This document describes the MCP tools available in the Highlight MCP Server.

## Overview

All tools are prefixed with `highlight_` to clearly identify them as CAST Highlight operations.

## Available Tools

### highlight_list_applications

List all applications in a CAST Highlight portfolio.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "domainId": {
      "type": "string",
      "description": "The domain ID to list applications from. If not provided, uses the default domain."
    },
    "limit": {
      "type": "number",
      "description": "Maximum number of applications to return. Default is 100."
    },
    "offset": {
      "type": "number",
      "description": "Number of applications to skip for pagination. Default is 0."
    }
  },
  "required": []
}
```

**Example Usage:**
```
List all applications in my portfolio
```

**Response:**
Returns a paginated list of applications with their IDs, names, and basic metadata.

---

### highlight_get_application

Get detailed information about a specific application.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "applicationId": {
      "type": "string",
      "description": "The unique identifier of the application."
    },
    "includeMetrics": {
      "type": "boolean",
      "description": "Whether to include health metrics. Default is true."
    },
    "includeTechnologies": {
      "type": "boolean",
      "description": "Whether to include technology breakdown. Default is true."
    }
  },
  "required": ["applicationId"]
}
```

**Example Usage:**
```
Get details for application app-12345
```

**Response:**
Returns comprehensive application information including metrics, technologies, and health scores.

---

## Planned Tools

### Phase 2

- **highlight_cloud_readiness** - Assess cloud migration readiness for an application
- **highlight_green_impact** - Get environmental impact metrics
- **highlight_software_health** - Get overall software health assessment
- **highlight_technical_debt** - Analyze technical debt

### Phase 3

- **highlight_compare_applications** - Compare metrics across multiple applications
- **highlight_trend_analysis** - Get historical trend data
- **highlight_recommendations** - Get AI-powered recommendations

## Error Handling

All tools return errors in a consistent format:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Error executing highlight_get_application: Application not found"
    }
  ]
}
```

## Best Practices

1. **Pagination**: Use `limit` and `offset` for large portfolios
2. **Selective Loading**: Use `includeMetrics: false` when you only need basic info
3. **Caching**: Results are cached based on `HIGHLIGHT_CACHE_TTL` setting
4. **Error Handling**: Always handle potential errors in tool responses
