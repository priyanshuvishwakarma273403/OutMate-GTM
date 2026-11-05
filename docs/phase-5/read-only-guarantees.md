# Strict Read-Only Guarantees — Outmate GTM CRM Layer

**Principle:** Non-destructive CRM Intelligence Access  
**Target:** HubSpot CRM  

---

## 1. Why Read-Only Is Non-Negotiable

Outmate GTM is an intelligence and research system. Enterprise customers authorize CRM access under strict data security constraints:
- Outmate must **never** overwrite existing CRM records.
- Outmate must **never** create unexpected marketing contacts, leads, or deals.
- Outmate must **never** initiate automated emails, outreach tasks, or lifecycle transitions.

---

## 2. Multi-Layer Enforcement Mechanism

Read-only guarantees are enforced across three independent defensive perimeters:

### Layer 1: HubSpot OAuth Scopes
During OAuth authorization, Outmate requests read-only scopes:
- `crm.objects.companies.read`
- `crm.objects.contacts.read`
- `crm.objects.deals.read`

HubSpot's OAuth gateway will reject any attempt to write or mutate data with `HTTP 403 Forbidden`.

### Layer 2: HubSpotAdapter Code Restrictions
The `HubSpotAdapter` class explicitly implements only read queries (`GET`, `POST /crm/v3/objects/*/search`). Any attempt to call mutation methods triggers an immediate exception:
```python
def _assert_read_only(self, action: str) -> None:
    raise CRMReadOnlyError(
        f"Operation '{action}' prohibited: Outmate GTM CRM access is strictly read-only."
    )
```

### Layer 3: Application & API Surface Restrictions
1. The FastAPI route definitions include only `GET` methods for CRM objects. No `POST`, `PUT`, `PATCH`, or `DELETE` endpoints exist under `/api/v1/crm/*`.
2. The MCP Server tool registry registers only search and get tools (`search_crm_*`, `get_crm_*`). No mutation tools exist.

