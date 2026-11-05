# Testing and Verification Guide — Phase 5 CRM Layer

**System:** Outmate GTM Platform  
**Test Suite:** Unit, Contract, and Integration Tests  

---

## 1. Test Architecture & Coverage

Phase 5 includes comprehensive test suites across unit, contract, and live integration boundaries:

| Test File | Focus Area | Status |
| :--- | :--- | :--- |
| `tests/unit/test_nango_client.py` | Connect session generation, token parsing, status checks, 401/429 errors | Passing |
| `tests/unit/test_hubspot_normalizers.py` | Company, contact, and deal payload parsing, number conversion, null safety | Passing |
| `tests/unit/test_hubspot_adapter.py` | Read-only guard, proxy URL construction, filter envelopes, context aggregation | Passing |
| `tests/unit/test_crm_service.py` | Tenant isolation, ownership validation, pending/connected states, research link | Passing |
| `tests/unit/test_mcp_crm_tools.py` | 18 tool registry check, scope enforcement, prompt injection sanitization | Passing |
| `tests/integration/test_integrations_api.py`| FastAPI integration endpoints, verify, disconnect, CRM data routes, UI HTML | Passing |
| `tests/integration/test_nango_hubspot_live.py`| Live network test against real Nango API (skipped when keys absent) | Guarded |

---

## 2. Running the Test Suite

### 2.1 Fast Unit & Contract Suite (Non-Live)
```bash
pytest -m "not live"
```
**Result:** 180 passed, 9 deselected, 0 failures.

### 2.2 Live Testing with Real Nango API
When `NANGO_SECRET_KEY` is provided in `.env`:
```bash
pytest tests/integration/test_nango_hubspot_live.py -m "live"
```
*Note: If `NANGO_SECRET_KEY` is missing, the test runner gracefully skips with `BLOCKED: NANGO_SECRET_KEY is not configured in the environment` rather than fabricating synthetic success.*

### 2.3 Strict Linting & Type Checking
```bash
ruff check app tests
ruff format --check app tests
mypy app
```
**Result:**
- `All checks passed!`
- `140 files already formatted`
- `Success: no issues found in 96 source files`

