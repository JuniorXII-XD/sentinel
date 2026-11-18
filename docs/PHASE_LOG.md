# Development phase log

## Phase 1 — Inspect and repair

Opened the exact Starter ZIP, inspected all source, README, dependencies and the three original tests. Original tests passed 3/3 before changes. Retained the pure repeated-failure function, Argon2 password-helper purpose, SQLAlchemy database setup and original entities. Identified unauthenticated demo APIs, incomplete IPv4 validation, no RBAC/session controls, missing migrations and count-only deduplication.

## Phase 2 — Models and authentication

Added config validation, users/role constraints, hashed opaque sessions, CSRF, expiry/revocation, database-backed login/API counters and Admin dependency. Created Alembic v0.1 baseline and forward Standard upgrade. Automated checks include blank and populated migration paths, authentication, cookie attributes, role changes and rate-counter concurrency.

## Phase 3 — Logging and detection

Added metadata allowlist and actual login/logout/denial/privilege/report audit records. Implemented five persisted rules, windows, cooldowns, evidence caps and isolated synthetic scenarios. Tests cover positive/negative thresholds, distribution, work hours, deduplication, rule disabling and partition separation.

## Phase 4 — REST APIs and authorization

Separated routers for authentication, monitoring, settings, demo and reports. Added typed validation, bounded bodies, origin/host controls, search/pagination, generic errors and backend RBAC. Security tests verify direct API denial, CSRF/origin failures, input handling and source-IP forwarding behavior.

## Phase 5 — Frontend

Built React/TypeScript/Vite with Tailwind, Lucide, Router and Recharts. Split screens into individual source files and shared layout/components. Dashboard and reports consume API responses. Build initially exposed a Vite configuration brace error; fixed before the first successful build. Captured the real Login UI from the same-origin FastAPI preview.

## Phase 6 — Investigation and reports

Added Admin-only status/notes, immutable API-visible history, evidence links and optimistic concurrency. Added summary/trend/severity/resolution reports in CSV/PDF, formula-cell escaping and export audit. Integration tests cover seed → metrics → search → investigate → resolve → export.

## Phase 7 — Hardening and integration

Extended backend tests and jsdom component/API tests. Found and fixed dependency advisories in the added frontend test tooling. The initial report-Blob unit assertion used a method missing in the jsdom Blob implementation; changed it to assert exported byte size. Kept the strict CSP and disabled CDN-dependent Swagger UI. See TEST_REPORT.md for final evidence and limits.

## Phase 8 — Documentation and packaging

Prepared English README, Thai installation/demo guide, architecture, schema snapshot, threat model, rule limitations, API reference, portfolio explanation and manual browser QA checklist. Added locked dependencies and optional unexecuted container configuration. Packaged source, built frontend and evidence while excluding databases, credentials, private environment settings, dependency directories and caches.


## Review patch 1.0.1 — 18 November 2026

Rechecked the unchanged v1.0 archive against working source and reran its backend suite: 50 passed, 17.08s, one dependency warning. Fixed quiet session probing, pair-based login throttling, explicit rule parameters, workspace subject migration, production hosts and private request-body handling. Reduced session-row updates while retaining shared DB API counters; the remaining SQLite bottleneck is documented.

Added migration 0003, 24 backend regression cases and one frontend component case. Final checks: backend 74 passed (30.20s), frontend 8 passed (3.44s), TypeScript/Vite build passed, fresh Alembic schema check reported no new operations. Updated setup, architecture, schema, API, detection and threat-model documentation. No dependency versions changed. No new public deployment, visual-browser QA, load testing or dependency audit was performed.
