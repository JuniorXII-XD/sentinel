# SENTINEL Standard — verification report

Date: **17 November 2026 (Asia/Bangkok)**. These results reflect commands actually executed during development. Tests are local and use synthetic events; no external attack, scan or production deployment occurred.

## Result summary

| Check | Actual result | Evidence |
| --- | --- | --- |
| Original Starter detector tests | **3 passed**, 0.01s, before changes | evidence/starter-tests.txt |
| Final backend automated suite | **50 passed**, 15.76s, 1 dependency deprecation warning | evidence/standard-tests.txt, evidence/pytest.xml |
| Frontend API/component suite | **7 passed**, 2 files, 1.79s, jsdom | evidence/frontend-tests.txt |
| TypeScript + production Vite build | **Passed**, 1,987 modules transformed | evidence/frontend-build.txt |
| Alembic model/schema convergence | **No new upgrade operations detected** | evidence/migration-check.txt |
| Upgrade populated Starter database | **Passed** inside backend suite; records/evidence/FKs checked | tests/test_migrations.py |
| npm dependency advisory audit | **0 known vulnerabilities** reported | evidence/npm-audit.json |
| Python pinned dependency advisory audit | **0 known vulnerabilities**, 37 dependencies, none skipped | evidence/python-audit.json |
| Local same-origin preview | FastAPI served built Login page successfully | screenshots/login-desktop.jpg |
| Desktop Login layout | Inspected at **1363 × 936**, document width 1363 (no horizontal overflow) | Screenshot and browser DOM measurement |
| Actual API-generated report files | CSV, PDF and summary successfully produced against disposable SQLite | sample-reports/ |
| PDF structure/text | A4, 1 page; pdfinfo and extracted text verified | sample-reports/sentinel-demo-7d.pdf |

The final sample report contains 215 synthetic events, 190 successful logins, 23 failed logins and 6 open alerts. Counts may differ when running on another date/time or after adding activity. They are actual generated database results, not hardcoded UI metrics.

## Backend coverage

- Argon2id hashes, successful/failed/unknown-user authentication and generic failures.
- HttpOnly / SameSite cookie, Secure / __Host- / HSTS behavior under secure configuration.
- Hashed session persistence, rotation, logout revocation, absolute and idle expiry.
- Login account throttling, suspicious-activity audit and repeated-failure detection.
- Concurrent DB rate-counter updates across connections.
- Origin rejection, CSRF failure, unauthenticated reads, Admin/Analyst enforcement.
- Analyst privilege denial creates an auditable detection signal.
- Account creation, duplicate username, self-change restriction and session revocation on access changes.
- Production configuration guards and disabled demo endpoint outside development.
- Body size limit, invalid host, wildcard rejection, CORS and forwarded-IP spoof resistance.
- Validation input redaction and generic unexpected-error response.
- Five rules: thresholds, negative cases, event windows, distinct accounts/sources, work-hour timezone, disabled rules, evidence merging and deduplication across a bucket boundary.
- Live/demo correlation separation and metadata allowlist.
- Full workflow: authenticated seed → dashboard aggregates → search → evidence → investigating → stale-update rejection → resolved → history → CSV/PDF.
- IP parsing, SQL-like search input, filter validation, CSV formula escaping and unknown object/API responses.
- Fresh migrations and nonempty v0.1 upgrade with foreign-key integrity and schema check.

## Frontend test scope

Vitest with jsdom tests the Fetch client, credentials/CSRF behavior, lack of localStorage writes, expiry notification, error propagation and downloadable bytes. Component interaction tests cover read-only Analyst investigation, Admin note/status payload including expected timestamp, and event filter requests/empty state.

These are simulated-DOM tests with controlled API responses. They are **not** a real-browser full-stack end-to-end suite and do not establish mobile visual correctness.

## Browser and environment limits

- Only desktop Login was visually inspected and captured. No authenticated Dashboard, Alert or Settings screenshot was produced.
- The browser tooling required user-controlled credential entry; automated sign-in using the local generated QA account was not performed. Authentication itself was tested by FastAPI TestClient.
- Mobile responsive CSS is implemented, but mobile/tablet viewports, touch behavior, keyboard accessibility and authenticated browser flows remain manually unverified. Follow MANUAL_QA.md.
- The initial preview startup timed out because the runner ignored the supplied port. The runner was corrected to parse host/port arguments; the next preview served correctly.
- One browser console message came from a browser extension; no application console error was observed on the inspected Login screen.
- PostgreSQL execution, Docker build, public deployment, load/stress testing, backup restore drill and independent penetration testing were not performed.
- No public URL is claimed. The available site runtime did not support running this Python FastAPI stack directly.

## Warnings and remediations

The final backend run has one Starlette TestClient deprecation warning: this installed version recommends httpx2. The requested FastAPI TestClient/httpx stack executed successfully; the warning is retained in raw evidence rather than suppressed. A future dependency update should revalidate the test transport.

The initially selected frontend test-tool version had npm advisories. `npm audit fix` updated the tooling; the final suite/build passed and the final audit reports zero. A Blob assertion was adjusted to match jsdom's supported Blob interface. These earlier failures are recorded in PHASE_LOG.md; final evidence reflects corrected code.

Python auditing used pinned dependencies with `pip-audit --disable-pip --no-deps`; every requirement in the lockfile was checked. Package hashes are not pinned, and advisory databases cannot prove absence of unknown issues. A zero advisory count is not a security certification.

## Reproduce

```bash
# Activated project virtual environment, from backend/
python -m pytest -q --junitxml=../docs/evidence/pytest.xml
alembic check
# From frontend/
npm test
npm run build
npm audit
# From project root, activated Python environment:
python scripts/generate_report_samples.py
```

For optional Python advisory checking install pip-audit separately, then run `pip-audit --disable-pip --no-deps -r backend/requirements.lock.txt --format json`. The auditing tool is not required to run the application.
