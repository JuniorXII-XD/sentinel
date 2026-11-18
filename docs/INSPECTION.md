# Starter v0.1 inspection

The exact named archive was retrieved and extracted before implementation. Its full source, README, dependency specification and original tests were inspected. A SHA-256 manifest is recorded in `evidence/starter-manifest.txt`.

The original repository contained a FastAPI module, SQLAlchemy User/SecurityEvent/Alert models, an Argon2 helper, a pure repeated-failure detector, three tests and short architecture/security notes. There was no frontend, database file, session manager, role dependency or migration system. Dependencies were broad ranges without a lockfile.

Original command: `python -m pytest -q` from the original backend, before source modification. Result: **3 passed in 0.01s**. Captured output: `evidence/starter-tests.txt`. This only exercised the pure detector, not authentication or API security.

| Finding | Evidence in original source | Standard response |
| --- | --- | --- |
| Public demo API | /demo/events, /demo/summary and /demo/alerts have no auth dependency | Removed original API routes; replacement /api/demo routes require development + enabled flag + Admin session + CSRF |
| No real accounts/sessions | User model and hash helper exist but no auth routes | Added login/logout, sessions, expiration, rate limits and account CLI |
| Invalid IPv4 octets accepted | Regex allows 1–3 arbitrary digits in last octet | Real IP parser + documentation-network membership |
| Fragile duplicate suppression | Alert only when len(recent)==5 | Rule/subject/time deduplication, unique fingerprint and evidence merging |
| Automatic schema creation | create_all at startup | Explicit Alembic revisions and upgrade tests |
| Unbounded reads | demo alerts lists all rows | Pagination and bounded evidence/report/detection queries |
| No browser client | No frontend directory | React routed SPA backed by real API calls |

The original `detect_repeated_failures` algorithm and its three tests remain. Database engine/FK setup and password-helper structure were retained and strengthened. Original models were extended through a migration that preserves existing records. No claim is made that the unmodified starter was attacked, externally scanned or production-tested.
