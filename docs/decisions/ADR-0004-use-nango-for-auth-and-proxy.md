# ADR-0004: Strict Scoping of Nango for Third-Party OAuth and API Proxying

## Status
Accepted

## Context
Enterprise GTM workflows require exporting verified decision-makers and intelligence dossiers into third-party CRMs (e.g. HubSpot, Salesforce). Building homemade OAuth token management, secret encryption at rest, token refresh loops, and provider-specific retry logic is complex, fragile, and error-prone.

However, using Nango for AI orchestration, internal state management, or hosting MCP servers would violate architectural boundaries and cause tool sprawl.

## Decision
We chose **Nango** strictly and exclusively for:
1. Third-party authentication and OAuth connection lifecycle management.
2. Secure third-party API proxy requests.

Nango is explicitly prohibited from participating in AI orchestration or MCP server hosting.

## Consequences

### Positive
- **Zero Token Storage in Application Code**: Third-party refresh tokens and access tokens are never retrieved or stored in Outmate's database; Nango injects authorization headers at the proxy layer.
- **Pre-Built CRM Connectors**: Out-of-the-box support for HubSpot, Salesforce, and other B2B platforms.
- **Clear Architectural Boundary**: Outmate's core research algorithms remain completely independent of external CRM OAuth state.

### Negative
- Relies on Nango Cloud or a self-hosted Nango instance for third-party sync operations.

