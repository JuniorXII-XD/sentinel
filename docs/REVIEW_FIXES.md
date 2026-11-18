# Standard 1.0.1 — review fixes

This patch addresses the five findings reported by the project owner. SENTINEL remains a personal defensive-security learning lab.

| Finding | Change | Files / verification |
| --- | --- | --- |
| Login page created high-risk events | `/auth/me` uses a dedicated quiet session probe. Missing/invalid sessions still return 401, but create no audit event or rate bucket. All validity checks remain. Other protected-resource denials remain audited. | `app/dependencies.py`, `routers/auth.py`; regression tests cover missing, invalid, expired, idle and disabled sessions and Overview counts |
| Username-global lockout DoS | Use 8 attempts per normalized username+trusted-source-IP pair / 300s, plus 20 total attempts per IP / 300s. Unknown usernames receive the same policy. The source comes from the ASGI connection, not arbitrary forwarding headers. | `routers/auth.py`; cross-IP, per-IP username rotation, spoofing and expiry tests |
| Hidden detection constants | Store `max_attempts_per_account`, `min_accounts`, `min_source_ips` in `detection_rules`, with migration/backfill and constraints. Engine reads persisted values. Settings displays the active numbers and explicitly states numeric parameters are read-only; only enabled can be changed via API/UI. Generic descriptions no longer hardcode numeric defaults. | `models.py`, `services/detection.py`, `routers/settings.py`, `SettingsPage.tsx`, migration 0003; tests change DB values and verify detection/UI |
| tenant subject in a single workspace | Use `workspace`; migrate existing AUTH-003 subjects and dedup fingerprints as well, retaining notes, evidence and status. | `services/detection.py`, migration 0003; populated Standard migration test |
| Hosts, private API and excessive session writes | Remove testserver from defaults; production requires explicit hosts and rejects testserver. Replace request._body with bounded public ASGI receive/replay. Conditional session activity refresh at most once per 30 seconds. | `config.py`, `middleware.py`, `main.py`, `dependencies.py`; production, streamed-body and session SQL-write regressions |

## Deliberate limits

- SQLite scaling is **partially mitigated only**. Session UPDATE frequency is reduced, but the shared atomic per-user API rate counter still needs one write/commit per authenticated request. No throughput claim or load test is supplied. Idle expiration can be up to 30 seconds earlier than exact per-request activity would imply.
- Pair-based login throttling removes cross-IP username-global lockout. It does not prevent shared-NAT/proxy users from affecting one another and is weaker against distributed password guessing. The IP-wide limit remains; no MFA or shared external limiter was added.
- Numeric rule tuning is not a new UI feature. Use a reviewed migration as a trusted local operator, test with synthetic events and keep a backup. ACCESS-001/AUTH-004 are single-event rules: their generic threshold field is explicitly unused; their window field is the deduplication cooldown.
- Existing false-positive `/auth/me` events are retained. This patch stops generating new ones; it does not rewrite investigation history or silently change historical metrics.
- PostgreSQL, Docker, mobile/browser interaction and production operations remain unverified in this patch.

## Upgrade

Keep the original `.env` and database. Stop writers, take a consistent backup, install the patched source, then run `alembic upgrade head` from `backend/`. Do not stamp an already versioned Standard database. Build the frontend from the project root with `npm --prefix frontend ci` and `npm --prefix frontend run build`, then restart. Migration 0003 is forward-only; restore the backup for rollback.

Migration tests verify populated v0.1 and v1.0 upgrades, foreign keys and schema/model convergence. The suite has 74 passing backend tests and 8 passing frontend tests. See `TEST_REPORT.md` and `evidence/review-*` for captured results.

## Middleware design reference

Starlette documents wrapping the public ASGI receive channel to inspect request bodies: https://www.starlette.io/middleware/#pure-asgi-middleware . The patch uses that protocol without mutating a private Request attribute. Its compatibility evidence is the installed locked dependency suite and the chunk/disconnect regression tests, not a guarantee for every future dependency version.
