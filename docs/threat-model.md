# Threat model — Standard 1.0.1

## Scope, assets and trust boundaries

Assets: account password hashes, session credentials, event records, investigation notes, rule configuration and reports. Actors: anonymous clients, authorized Analysts, Admins, local operators, database administrators and a potential malicious user. The application is a single shared workspace; an Analyst may read all security data in that workspace.

Boundaries: browser → HTTP server; cookie → DB session; route → authorization dependency; validated input → ORM; real events ↔ synthetic events; DB → CSV/PDF export. The local operator and DB administrator are trusted to manage the installation and can modify stored evidence. No external host is scanned or contacted by demo generation.

| Threat | Implemented control | Remaining limitation |
| --- | --- | --- |
| Credential guessing | Argon2id; generic login failures; dummy hash; username+source-IP and total-per-IP fixed-window throttles; failure audit | No MFA; rotating sources can bypass pair limits; shared NAT/proxy users can still deny each other login; no formal timing proof |
| Session theft/fixation | Random 256-bit session secret; DB digest; cookie rotation on login; HttpOnly; Strict SameSite; Secure/__Host- under HTTPS; idle/absolute expiry | XSS can still act as a user; stolen active cookie remains valuable until revocation |
| CSRF, including login CSRF | Exact Origin allowlist on mutations; session-bound CSRF header on authenticated mutations | Assumes trusted origins are securely operated; same-origin XSS bypasses CSRF protections |
| Role bypass / direct API calls | Server-side Admin dependency; role lookup from DB; denied-action audit and detection | No per-record permissions within the shared workspace |
| SQL injection | ORM expressions and bound parameters; escaped literal search | Database credentials/host still need secure operations |
| Stored XSS | React escaped text; no unsafe HTML insertion; restrictive CSP | Style inline allowance needed by charts; no independent penetration test |
| Secret exposure | Metadata allowlist; validation responses omit input; generic 500; hashed sessions; no raw passwords in audit | Operators must avoid secrets in free-text notes; DB access reveals hashes/notes/CSRF values |
| Log/alert tampering | Admin-only mutations; append-only API history; optimistic concurrency | DB administrators can rewrite rows; no signed/remote append-only archive |
| Demo exposure | Disabled by default; development-only; Admin + CSRF + rate limit; documentation IP validation | Development services must remain protected; no public deployment performed |
| Resource exhaustion | Bounded mutation body; bounded fields; DB rate counters; query/evidence/export caps | No edge/global traffic limiter; malformed/pre-auth traffic can still consume resources; no load test |
| CSV spreadsheet execution | Prefix formula-looking cells with an apostrophe; CSV escaping | Review exported files under the organization's spreadsheet policy |
| Forged source address | Default server ignores arbitrary forwarding headers | Reverse-proxy deployments need explicit tested source-IP handling |
| Supply-chain compromise | Pinned Python lock and npm lock; captured npm and Python audits | Advisory coverage is incomplete; a clean audit is not a security proof |

## Security defaults

Production configuration requires HTTPS origins, secure cookies, disabled demo and explicitly supplied ALLOWED_HOSTS without testserver. Development defaults contain only localhost and 127.0.0.1. Wildcard hosts/origins are rejected. OpenAPI documentation is disabled in production. Cookies have no Domain attribute and use Path=/; HTTPS session cookie name uses the `__Host-` prefix. CORS does not allow arbitrary credentialed origins. Mutation size is limited to 16 KiB before JSON validation. Tests verify that rejected input does not echo supplied password data.

Login is limited to 8 attempts per normalized username+source-IP pair and 20 total attempts per source IP per 300 seconds. There is deliberately no username-global lockout: one remote source cannot continually lock that account for all other sources. The tradeoff is weaker prevention of distributed guessing; AUTH-003 provides a review signal, not a block. Users behind one NAT or a reverse proxy without correctly configured proxy trust still share the IP and can affect each other.

Rate-limit counters store SHA-256 identifiers and apply whether or not a username exists. The fixed-window scheme can permit bursts at window boundaries and can deny legitimate shared-IP users. Login limits count successful attempts too within their window; do not use this as an enterprise identity service without tuning.

## Security review results

Starter v0.1 had public demo read/write APIs, no session or RBAC checks, no migrations, a weak IPv4 regex accepting out-of-range octets, and deduplication based only on `len(recent)==5`. Standard replaces the demo routes with authenticated development-only endpoints, uses real IP parsing, stores explicit rules/history/evidence and adds migration/test coverage. The retained pure repeated-failure detector passed its three original tests before development began.

Remaining release gates before production: real PostgreSQL testing, load testing, mobile/authenticated browser QA, MFA/SSO decision, TLS/proxy configuration, ongoing dependency advisory review, backup restore exercise, log retention, monitoring/alert delivery and independent security assessment.

## Design references

- OWASP CSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- FastAPI response cookies: https://fastapi.tiangolo.com/advanced/response-cookies/
- SQLAlchemy documentation: https://docs.sqlalchemy.org/en/20/
- Alembic migrations: https://alembic.sqlalchemy.org/en/latest/

These references inform the design; they do not certify this implementation.

## Audit noise and storage contention

The session-status endpoint `/api/auth/me` is expected to be called before login and after expiry. Its 401 responses are not security events and do not consume audit counters. Protected resource denials remain high-severity events; authenticated Admin-only denials still feed ACCESS-001. Rate-limited public API abuse can still create noisy denial records. The patch does not delete historical false positives.

Session `last_seen_at` uses a conditional UPDATE only after 30 seconds since the stored activity. Idle expiry is conservative by up to 30 seconds. The shared atomic API rate counter still performs a write and commit on every authenticated request, including `/auth/me`; SQLite serializes writes, so this is still a throughput limit. This release has no load-test evidence. Moving rate counters to a shared service and testing PostgreSQL concurrency are future scaling work, not implemented fixes.
