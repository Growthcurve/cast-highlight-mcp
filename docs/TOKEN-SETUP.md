# CAST Highlight API Token Setup Guide

This guide walks through the process of setting up API token authentication for the CAST Highlight REST API.

## Overview

CAST Highlight supports two authentication methods:
- **Basic Authentication** - Username and password (can be disabled at company level)
- **OAuth2 Bearer Token** - Recommended for API integrations and automation

This guide covers setting up OAuth2 Bearer Token authentication.

## Prerequisites

- CAST Highlight account with administrative access
- Access to the Token Management page (requires appropriate permissions)

---

## Step 1: Enable Token Management (Company Admin)

A company administrator must first enable token management for the organization.

1. Log in to [CAST Highlight](https://app.casthighlight.com)
2. Navigate to **COMPANIES** in the top navigation bar
3. Select **Token Management** from the dropdown menu

![Token Management Navigation](./images/cast-highlight-token-setup.gif)
*Navigate to COMPANIES → Token Management*

### Configure Company OAuth Settings

On the Token Management page, configure the following:

| Field | Description |
|-------|-------------|
| **Activate token management** | Toggle to "Yes" to enable OAuth tokens. **Note:** This disables Basic Authentication for the company. |
| **Client Id** | Auto-generated identifier for your company (read-only) |
| **Secret** | Enter a secure alphanumeric string of your choice |
| **Token Validity (minutes)** | How long tokens remain valid. Default: 525600 (365 days) |

![Token Management Configuration](./images/token-management-empty.png)
*Token Management page showing configuration options and empty token table*

> **Important:** Save the **Client Id** and **Secret** securely. You will need both to authenticate API requests.

4. Click **Apply** to save the configuration

---

## Step 2: Generate Your Personal Access Token

Each user who needs API access must generate their own token.

1. Click on your **user icon** in the top-right corner of the page
2. Select **Generate Access Token** from the dropdown menu

3. A modal will appear displaying your new token:

```
API Access token
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Token expires in 525600 minutes.
Call API using header 'Authorization: Bearer your token'
```

> **Critical:** Copy and save this token immediately. It may not be displayed again.

4. Close the modal
5. **Refresh the page** to see your token listed in the token table

---

## Step 3: Using Your Token

### API Request Format

Include your token in the `Authorization` header of all API requests:

```bash
curl -X GET "https://rpa.casthighlight.com/WS2/domains" \
  -H "Authorization: Bearer xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Environment Variables

For the CAST Highlight MCP server, configure these environment variables:

```bash
# .env
HIGHLIGHT_DOMAIN=your-company.casthighlight.com
HIGHLIGHT_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Or using Client Id and Secret for OAuth2 flow:

```bash
# .env
HIGHLIGHT_DOMAIN=your-company.casthighlight.com
HIGHLIGHT_CLIENT_ID=YOUR_COMPANY - PortCos_XXXX
HIGHLIGHT_CLIENT_SECRET=your-secret-here
```

---

## Token Management

### Viewing Active Tokens

The Token Management page displays all active tokens for your company:

| Column | Description |
|--------|-------------|
| **Token** | The token identifier (UUID format) |
| **Validity** | Expiration date and time |
| **User** | Email of the user who generated the token |
| **Role** | User's role (e.g., portfolioManager) |

### Revoking Tokens

To revoke a token:
1. Navigate to **COMPANIES** → **Token Management**
2. Find the token in the table
3. Click the **trash icon** on the right side of the row

> **Note:** Revoking a token immediately invalidates it. Any integrations using that token will stop working.

### Token Expiration

- Tokens expire based on the **Token Validity** setting configured by the company admin
- Default validity is 525600 minutes (365 days)
- Users must generate a new token before expiration to maintain API access

---

## Troubleshooting

### "401 Unauthorized" Response

- Verify the token has not expired
- Ensure the token is correctly formatted in the Authorization header
- Check that token management is enabled for your company

### Token Not Appearing in Table

- Refresh the Token Management page after generating a new token
- The table may require a page reload to display newly created tokens

### Cannot Generate Token

- Verify token management is enabled (toggle set to "Yes")
- Ensure you have the necessary permissions
- Contact your company administrator if the option is not available

---

## Security Best Practices

1. **Never commit tokens to version control** - Use environment variables or secrets management
2. **Use separate tokens for different integrations** - Makes revocation easier
3. **Rotate tokens periodically** - Generate new tokens and revoke old ones
4. **Monitor token usage** - Review the Audit Logs for suspicious activity
5. **Use minimal token validity** - Set expiration appropriate to your use case

---

## Related Documentation

- [API Reference](./API.md) - Complete API endpoint documentation
- [CAST Highlight Official Docs](https://doc.casthighlight.com/feature-focus-api-cli-user-token-management/) - Official token management guide
