# API reference

Prefix `/api`; JSON responses except report export. The same-origin browser Fetch client is in `frontend/src/api.ts`. Development OpenAPI JSON is available at `/api/openapi.json`. The CDN-backed interactive Swagger page is deliberately disabled so the self-only CSP remains consistent. Production disables the schema endpoint too.

| Method / route | Role | Purpose |
| --- | --- | --- |
| GET /health | Public | Process/version health, not database readiness |
| POST /auth/login | Public + trusted Origin | Username/password → session cookie, public user, CSRF token |
| GET /auth/me | Authenticated | User, CSRF token and demo availability; missing/invalid session returns quiet 401 |
| POST /auth/logout | Authenticated + CSRF | Delete current session, clear cookie, audit logout |
| GET /overview | Authenticated | Aggregate dashboard metrics and timelines |
| GET /events | Authenticated | Search/filter/paginate events |
| GET /alerts | Authenticated | Filter/paginate alerts |
| GET /alerts/{id} | Authenticated | Alert, evidence and history |
| PATCH /alerts/{id} | Admin + CSRF | Status and investigation note with optimistic concurrency |
| GET /settings | Authenticated | Rules and non-secret environment policy |
| GET /settings/users | Admin | Up to 500 workspace accounts, no password hashes |
| POST /settings/users | Admin + CSRF | Create account (username normalized to lowercase) |
| PATCH /settings/users/{id} | Admin + CSRF | Role/activation change; revoke target sessions; no self-change |
| PATCH /settings/rules/{id} | Admin + CSRF | Enable/disable detection rule; audit change |
| POST /demo/events | Development Admin + CSRF | Insert one validated synthetic authentication event |
| POST /demo/seed | Development Admin + CSRF | Idempotent internally generated scenario dataset |
| GET /reports/summary | Authenticated | Aggregate report JSON |
| POST /reports/export | Authenticated + CSRF | Audited CSV or PDF attachment |

All mutating routes also require an Origin in the exact server-side allowlist. The browser sets Origin itself; clients must not use arbitrary origins. No authentication token is stored in localStorage.

## Common filters

`scope=live|demo` (default live); `days=1..90` (default 7, rolling window). Events/alerts: `page>=1`, `page_size=1..100` (default 20). Events support `q`, `event_type` and `severity`; alerts support `status` and `severity`. Invalid enum values return 422. Queries are parameterized; search wildcard characters are escaped.

## Investigation mutation

```json
{
  "status": "investigating",
  "note": "Reviewed the documented IP and correlated failed logins.",
  "expected_updated_at": "<exact updated_at from the latest alert response>"
}
```

A note is required for every update (1–2,000 characters after trimming). Status can be open, investigating or resolved. A same-status update adds a note/history entry. A stale timestamp returns 409; fetch the latest alert before retrying. Notes should not contain passwords or secrets.

## Response handling

401: missing/expired session or invalid login. 403: Origin, CSRF or role failure. 404: missing object or disabled demo endpoint (after authentication). 409: username conflict or stale alert update. 413: request body too large. 422: validation failure without raw input. 429: throttled, with Retry-After. 500: generic internal failure; no stack trace or SQL parameters returned.

Reports use POST because exporting is audited. Query parameters: `format=csv|pdf`, `scope`, `days`. Response includes attachment Content-Disposition. CSV caps detailed events at 10,000 and includes summary/trends/recommendations. PDF includes a paginated English summary and daily trends; arbitrary notes are not rendered into PDF.

Numeric detection fields in GET `/settings` are read-only: `threshold`, `window_seconds`, `max_attempts_per_account`, `min_accounts`, `min_source_ips`. PATCH `/settings/rules/{id}` accepts only `enabled`; extra fields return 422. Login throttles use username+source-IP pairs (8/300s) and total source IP (20/300s), not username-global lockouts.
