# CAST Highlight API Reference

This document describes the CAST Highlight REST API endpoints available for integration.

**Official Documentation**: https://rpa.casthighlight.com/api-doc/index.html#/

## Base URL

```
https://rpa.casthighlight.com/WS2
```

## Authentication

The CAST Highlight API uses Basic Authentication or OAuth2.

```
Authorization: Basic {base64(username:password)}
```

---

## API Endpoints by Category

### Administration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/companies/{companyId}` | Retrieve company details |
| GET | `/companies/{companyId}/audit` | Retrieve company audit log |
| POST | `/company` | Create new company |
| PUT | `/company` | Update existing company |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/administrator/users` | List all admin users |
| POST | `/administrator/users` | Add new admin user |
| DELETE | `/administrator/users/{id}` | Remove admin user |

### Domains

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}` | Retrieve domain details |
| GET | `/domains/industrySegment` | Get available industry segments |
| POST | `/domains/surveys` | Assign surveys to domains |
| GET | `/domains/{domainId}/health` | Domain health status |
| GET | `/domains/{domainId}/technologies` | Technologies detected in domain |
| GET | `/domains/{domainId}/tags` | Domain-scoped tags |
| GET | `/domains/{domainId}/segmentations` | Domain-specific segmentations |

### Applications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications` | List all applications in domain |
| POST | `/domains/{domainId}/applications` | Create or update applications |
| GET | `/domains/{domainId}/applications/{applicationId}` | Get application details |
| POST | `/domains/{domainId}/applications/{applicationId}` | Update specific application |
| DELETE | `/domains/{domainId}/applications/{applicationId}` | Delete application |
| GET | `/domains/{domainId}/applications/clientref/{clientRef}` | Get application by client reference |

### Application Results & Snapshots

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/results` | List all application results |
| GET | `/domains/{domainId}/applications/{applicationId}/results/{resultId}` | Get specific application result |
| GET | `/domains/{domainId}/applications/{applicationId}/appResultSnapshot/{applicationResultId}` | Get application snapshot details |

### Components

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/components` | Retrieves component details |
| GET | `/domains/{domainId}/applications/{applicationId}/components/{projectId}` | Get specific component/project |
| GET | `/domains/{domainId}/applications/{applicationId}/components/mapping` | Get fingerprint file mapping |
| GET | `/domains/{domainId}/applications/{applicationId}/components/{projectId}/mapping` | Get fingerprint mapping for project |

### Vulnerabilities (CVE)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/vulnerabilities` | Fetch vulnerability list for application |
| GET | `/domains/{domainId}/vulnerabilities` | Domain-level vulnerability aggregation |
| POST | `/domains/{domainId}/applications/vulnerabilities/aggregated` | Get CVE aggregation by application |

### Dependencies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/dependencies` | Lists application dependencies |
| GET | `/domains/{domainId}/dependencies` | Domain-level dependency information |

### Frameworks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/frameworks` | Retrieves frameworks used by application |
| GET | `/frameworks` | Lists all available frameworks |

### Licenses

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/licenses` | Application license information |
| GET | `/licenses` | All licenses across system |

### Technologies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/technologies` | Available technology catalog |
| GET | `/domains/{domainId}/technologies` | Technologies detected in domain |

### Cloud Readiness

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/cloud/data/{domainId}` | Get cloud readiness data |
| GET | `/cloud/containerization/{domainId}` | Get cloud containerization analysis |
| GET | `/cloud/requirements/{domainId}` | Get cloud patterns for domain |
| GET | `/cloud/transferability/{domainId}` | Get cloud transferability analysis |
| GET | `/cloud/pattern` | Retrieve all cloud pattern definitions |
| GET | `/cloud/pattern/{key}` | Get specific cloud pattern definition |
| GET | `/domains/{domainId}/applications/{applicationId}/containerization` | Get containerization for application |
| GET | `/domains/{domainId}/applications/{applicationId}/recommendation` | Get cloud recommendations |
| PUT | `/domains/{domainId}/applications/{applicationId}/recommendation/custom/{platformId}/{serviceId}` | Add custom cloud recommendation |
| DELETE | `/domains/{domainId}/applications/{applicationId}/recommendation/custom/{platformId}/{serviceId}` | Delete custom recommendation |

### Alerts & Risks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/alerts` | Retrieve top 20 alerts by domain |
| POST | `/domains/{domainId}/alerts` | Get filtered alerts by domain |
| POST | `/domains/{domainId}/alerts/applications` | Get applications triggered alerts |
| GET | `/domains/{domainId}/applications/{applicationId}/alerts` | Get top risks for application |
| POST | `/alerts/exclusion` | Create or update code insight exclusion |
| DELETE | `/alerts/exclusion` | Delete code insight exclusion |
| GET | `/alerts/exclusion/{applicationId}` | Get code insight exclusions |
| GET | `/alerts/recompute/{applicationResultId}` | Trigger Code Insight recompute |

### Tags

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tags` | All available tags |
| GET | `/domains/{domainId}/tags` | Domain-scoped tags |
| POST | `/domains/{domainId}/applications/{applicationId}/tags` | Assigns tags to application |
| DELETE | `/domains/{domainId}/applications/{applicationId}/tags/{tagId}` | Removes tag from application |

### Benchmark

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/benchmark` | Retrieve benchmark metrics |
| GET | `/benchmark/alerts` | Get benchmark alerts by technology |
| POST | `/benchmark/alerts` | Get filtered benchmark alerts |

### Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/metrics` | System metrics collection |
| POST | `/metrics/query` | Query specific metrics with filters |

### Segmentations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/segmentations` | Lists all segmentation categories |
| POST | `/segmentations` | Creates new segmentation |

### Goal Tracking

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/goaltracking` | Get current goal tracking indicators |
| GET | `/domains/{domainId}/applications/{applicationId}/goaltracking/trend` | Get goal tracking trends |

### Keywords

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/keyword` | Get keywords from last result |

### Conversations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/conversation` | Retrieve conversation messages |
| POST | `/domains/{domainId}/applications/{applicationId}/conversation` | Add conversation message |
| GET | `/domains/{domainId}/applications/{applicationId}/conversation/status` | Get conversation message count |
| DELETE | `/domains/{domainId}/applications/{applicationId}/conversation/{id}` | Delete conversation message |

### Export/Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/domains/{domainId}/applications/{applicationId}/export` | Generate export report (async) |
| GET | `/domains/{domainId}/applications/{applicationId}/export/{reportId}` | Download generated report |

### AI Assistant

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ai/enable/domain/{domainId}` | Check if AI Assistant enabled |
| GET | `/ai/key/domain/{domainId}` | Get AI Assistant API key |
| POST | `/ai/key/domain/{domainId}` | Update AI Assistant API key |
| POST | `/ai/message/{domainId}` | Send message to AI Assistant |
| GET | `/ai/AiParameter/id/{aiId}` | Retrieve AI parameter configuration |

### Campaigns & Surveys

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/domains/{domainId}/applications/{applicationId}/campaigns/{campaignId}/submit` | Submit application results for campaign |
| POST | `/domains/{domainId}/applications/{applicationId}/campaigns/{campaignId}/surveys/{surveyId}` | Answer survey for application |

---

## Common Query Parameters

### Pagination
- `limit` - Maximum results to return (default varies by endpoint)
- `offset` - Number of items to skip

### Filtering (Applications)
- `technologyIds` - Filter by technology IDs
- `metricIds` - Filter by metric IDs
- `tagIds` - Filter by tag IDs

### Expansion
- `expand` - Include additional nested data (e.g., `metrics`, `technologies`)

---

## Error Handling

### Error Response Format

```json
{
  "code": "INVALID_REQUEST",
  "message": "The request was invalid",
  "details": {
    "field": "applicationId",
    "reason": "Not found"
  }
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (success, no body) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Internal Server Error |

---

## Rate Limiting

- Check `X-RateLimit-Remaining` header for remaining requests
- Check `X-RateLimit-Reset` header for reset timestamp
- Implement exponential backoff on 429 responses
