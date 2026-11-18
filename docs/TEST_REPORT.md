# SENTINEL Standard 1.0.1 — review regression report

Date: **18 November 2026 (Asia/Bangkok)**. This report describes commands actually executed for the five review findings. All tests used local synthetic data. No external scanning or deployment occurred.

## Actual results

| Check | Result | Evidence |
| --- | --- | --- |
| Unchanged v1.0 baseline, before edits | 50 passed, 17.08s; one TestClient deprecation warning | Baseline command observed during this review; original release evidence also retained |
| Updated full backend suite | **74 passed, 30.20s**, one TestClient deprecation warning | evidence/review-backend-tests.txt, evidence/review-pytest.xml |
| Updated frontend suite | **8 passed**, 3 files, 3.44s | evidence/review-frontend-tests.txt |
| TypeScript + Vite production build | **Passed**, 1,987 modules transformed, Vite 4.18s | evidence/review-frontend-build.txt |
| Fresh SQLite migration + schema/model convergence | **No new upgrade operations detected** | evidence/review-migration-check.txt |
| Populated Starter and Standard upgrades | **Passed** within backend suite; notes, evidence, parameters and FKs checked | backend/tests/test_migrations.py |

## Added regression evidence

- Three anonymous session probes create zero events and zero audit counters. The next authenticated Overview reports zero high-risk events. Invalid, expired, idle-expired and disabled-user sessions return quiet 401 on `/auth/me`.
- Direct anonymous access to protected data still creates an unauthorized-access audit record; existing tests retain authenticated privilege-denial detection, CSRF and revocation coverage.
- Eight bad attempts exhaust the username+IP pair; the ninth gets 429. A different IP can still authenticate that username. Another account on the first IP retains its own pair budget.
- Rotating usernames and spoofing X-Forwarded-For cannot bypass the 20-attempt source-IP budget. Expired fixed-window counters recover without sleeping.
- Three authenticated requests do not update the session row within 30 seconds, but do increment API rate counters. A later activity refresh updates the session, and an exhausted API budget still returns 429.
- Production rejects implicit host defaults and testserver; explicit environment hostnames are accepted.
- Nondefault database parameters change AUTH-002/003 behavior. Required and positive parameter constraints reject invalid values. AUTH-003 uses workspace in both subject and fingerprint.
- Settings exposes the numeric fields; mutation attempts remain rejected with 422. Frontend component coverage displays nondefault server values, explains read-only numeric parameters and disables Analyst rule switches.
- ASGI multi-chunk bodies at 16,384 bytes pass; 16,385 bytes get 413 before the downstream app runs. Valid JSON at the limit reaches login. Early disconnect is handled and disconnect after replay remains observable.
- Migration 0003 retains an existing investigation note, alert state and evidence, preserves operator-tuned threshold/window/enabled values, backfills new parameters and rewrites tenant scope/fingerprint to workspace.

## Limits and warnings

The installed Starlette TestClient emits one deprecation warning recommending httpx2. Tests passed without suppressing it. npm emits an environment-level unknown http-proxy configuration warning; the test and build commands exited successfully.

No new dependencies were introduced. The package-lock application version changed to 1.0.1; package dependency versions did not change. Advisory audit files from the original release are retained as **historical evidence**, not a fresh security audit. See evidence/TEST_REPORT_v1.0.md for the original release record.

No new browser screenshots, authenticated-browser checks, mobile visual checks, PostgreSQL execution, Docker build, load tests or public deployment were performed. Frontend tests use jsdom with controlled API responses; they are not real-browser full-stack end-to-end tests. The bundled Login screenshot and sample reports are from v1.0 and are retained for reference.

Coalescing session writes does **not** eliminate SQLite contention: shared API rate counters still write and commit on each authenticated request. A username+IP limit reduces cross-source account lockout, but shared NAT/proxy users still share limits and distributed guessing remains possible. Historical false-positive events are retained, not silently erased.

## Reproduce

From backend/ with the project Python virtual environment active:

```bash
python -m pytest -q --junitxml=../docs/evidence/review-pytest.xml
alembic upgrade head
alembic check
```

Run migration commands against a backed-up development database with application writers stopped. Pytest itself uses isolated temporary databases.

From frontend/:

```bash
npm ci
npm test
npm run build
```
