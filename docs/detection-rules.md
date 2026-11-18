# Detection rules and limitations

All rules produce **signals for investigation**, never a finding that an attack is confirmed. Numeric parameters are seeded into `detection_rules` and read from the database by the detector. Settings displays these current values as read-only; its API permits only enabling/disabling. Tuning requires a trusted local operator and a reviewed database migration. No arbitrary detection code is accepted. The table below shows the default configuration, not immutable constants.

| ID | Trigger | Severity | Window / subject | Likely false positives |
| --- | --- | --- | --- | --- |
| AUTH-001 | At least 5 failed logins from a single IP | High | 60s / IP | Shared NAT, forgotten passwords, broken clients |
| AUTH-002 | Failures against at least 5 account identifiers from one IP, maximum 2 failures per account in the window | High | 300s / IP | Training exercise, shared office sign-ins |
| AUTH-003 | At least 10 failed logins across 3 account identifiers and 2 sources | Medium | 300s / workspace | Broad identity-provider outage, scheduled testing |
| ACCESS-001 | A signed-in account is denied an Admin-only operation | Critical | 300s / user ID | Incorrect role assignment, old bookmarks, exploratory use |
| AUTH-004 | Successful login outside 07:00–22:00 in configured timezone | Low | 3600s / account | Shift work, travel, exam preparation |

AUTH-002 cannot prove that one password was used against many accounts: passwords are deliberately never logged. Its name describes a pattern consistent with spraying, not direct password comparison. Increasing attempts on one account may stop this rule while triggering AUTH-001. AUTH-003 is a workspace-wide failure-cluster heuristic, not attribution of a coordinated campaign. ACCESS-001's Critical label means investigate urgently; the request has already been denied, so it does not establish privilege escalation.

## Windows and deduplication

Correlation includes events in `[current event time - window, current event time]`, at most 1,000 recent matching records. Incoming demo API timestamps cannot be supplied by the client. Historical seed timestamps are generated internally. Live/demo records are never combined.

A rule+subject+partition lookup suppresses additional alerts whose creation falls within the cooldown window, even across fixed bucket boundaries. Suppressed triggers add evidence (maximum 200 links) instead of creating another alert. A unique rule/subject/partition/time-bucket key also rejects concurrent duplicates within a bucket. Resolved alerts suppress new duplicates during the same cooldown; after cooldown a new incident may be created. Old alerts are not automatically reopened or silently reclassified.

The unique bucket guard does not prove exactly-once delivery across every PostgreSQL boundary race; cross-worker PostgreSQL concurrency has not been tested. SQLite request write locking and database-backed counters substantially serialize this lab's writes. A scaled deployment should use a transactionally locked per-subject detection-state record.

## Interpretation and tuning

Expected business impact: administrators can prioritize credential and permission anomalies and maintain an investigation record. False positives can waste staff time; false negatives remain possible for slow or distributed attacks outside these windows. Thresholds are educational defaults, not validated for a particular company. Work-hour schedules should reflect actual operations.

Demo scenarios: baseline sign-ins; seven repeated failures from 192.0.2.42; six accounts from 198.51.100.24; ten distributed failures; one denied privilege operation; one off-hours login. Documentation IPs do not represent systems that were contacted.

## Parameter semantics (migration 0003)

| Rule | Active database fields |
| --- | --- |
| AUTH-001 | `threshold`: minimum failures; `window_seconds`: correlation/cooldown |
| AUTH-002 | `threshold`: distinct accounts; `max_attempts_per_account`: cap per account; `window_seconds`: correlation/cooldown |
| AUTH-003 | `threshold`: failures; `min_accounts`: distinct accounts; `min_source_ips`: distinct sources; `window_seconds`: correlation/cooldown |
| ACCESS-001 | Single authenticated denial; `window_seconds`: cooldown only; generic `threshold` field is unused |
| AUTH-004 | Single successful off-hours login; environment work hours/timezone; `window_seconds`: cooldown only; generic `threshold` field is unused |

Rule-specific parameters are positive integers with required-field constraints for AUTH-002/003; irrelevant fields are null. Operator changes are used on the next evaluation; existing alerts are not reclassified. Reduce thresholds carefully and test with synthetic events. Back up the database and stop writers before migrating. AUTH-003 uses `workspace` as its subject; migration 0003 updates existing subjects and dedup keys to preserve suppression.
