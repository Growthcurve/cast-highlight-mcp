# MCP Tools Documentation

This document describes the MCP tools available in the Highlight MCP Server.

## Overview

All tools are prefixed with `highlight_` to clearly identify them as CAST Highlight operations.

## Available Tools

### highlight_get_company

Get company details including domain count, application count, and status.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "company_id": {
      "type": "integer",
      "description": "Company ID (optional, uses default from config)"
    }
  }
}
```

**Example Usage:**
```
Get my company details
```

---

### highlight_list_domains

List all domains/portfolios for the company.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "company_id": {
      "type": "integer",
      "description": "Company ID (optional, uses default from config)"
    }
  }
}
```

**Example Usage:**
```
List all domains in my portfolio
```

---

### highlight_get_domain

Get details for a specific domain/portfolio.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "domain_id": {
      "type": "integer",
      "description": "Domain ID"
    }
  },
  "required": ["domain_id"]
}
```

**Example Usage:**
```
Get details for domain 12345
```

---

### highlight_list_applications

List all applications in a domain with their health metrics.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "domain_id": {
      "type": "integer",
      "description": "Domain ID"
    }
  },
  "required": ["domain_id"]
}
```

**Example Usage:**
```
List all applications in domain 12345
```

---

### highlight_get_application

Get detailed information about a specific application.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "application_id": {
      "type": "integer",
      "description": "Application ID"
    }
  },
  "required": ["application_id"]
}
```

**Example Usage:**
```
Get details for application 67890
```

---

### highlight_get_metrics

Get health metrics for an application (software health, agility, elegance, resiliency).

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "application_id": {
      "type": "integer",
      "description": "Application ID"
    }
  },
  "required": ["application_id"]
}
```

**Example Usage:**
```
Get health metrics for application 67890
```

---

### highlight_get_technologies

Get technology breakdown for an application (languages, frameworks, libraries).

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "application_id": {
      "type": "integer",
      "description": "Application ID"
    }
  },
  "required": ["application_id"]
}
```

**Example Usage:**
```
What technologies does application 67890 use?
```

---

### highlight_get_cloud_readiness

Get cloud migration readiness assessment for an application.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "application_id": {
      "type": "integer",
      "description": "Application ID"
    }
  },
  "required": ["application_id"]
}
```

**Example Usage:**
```
Is application 67890 ready for cloud migration?
```

---

### highlight_get_green_impact

Get environmental/green impact metrics for an application.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "application_id": {
      "type": "integer",
      "description": "Application ID"
    }
  },
  "required": ["application_id"]
}
```

**Example Usage:**
```
What's the green impact score for application 67890?
```

---

### highlight_get_cves

Get CVE vulnerabilities affecting an application's dependencies.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "application_id": {
      "type": "integer",
      "description": "Application ID"
    }
  },
  "required": ["application_id"]
}
```

**Example Usage:**
```
Show CVE vulnerabilities for application 67890
```

---

### highlight_get_third_parties

Get third-party/open-source components used by an application.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "application_id": {
      "type": "integer",
      "description": "Application ID"
    }
  },
  "required": ["application_id"]
}
```

**Example Usage:**
```
What open source components does application 67890 use?
```

---

### highlight_get_benchmark

Get benchmark statistics comparing against all CAST Highlight applications globally.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

**Example Usage:**
```
Show global benchmark statistics
```

---

## Error Handling

All tools return errors in a consistent format:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Error: Application not found"
    }
  ]
}
```

## Best Practices

1. **Start with Company**: Use `highlight_get_company` to get your company ID and see available domains
2. **List Domains**: Use `highlight_list_domains` to discover available portfolios
3. **List Applications**: Use `highlight_list_applications` with a domain ID to see applications
4. **Deep Dive**: Use specific tools (`highlight_get_metrics`, `highlight_get_cves`, etc.) for detailed analysis
5. **Error Handling**: Always handle potential errors in tool responses
