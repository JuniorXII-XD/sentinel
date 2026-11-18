-- SQLite schema snapshot, migration 0003. No user data. Migrations are authoritative.

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

CREATE TABLE alert_evidence (
	alert_id INTEGER NOT NULL, 
	event_id INTEGER NOT NULL, 
	PRIMARY KEY (alert_id, event_id), 
	FOREIGN KEY(alert_id) REFERENCES alerts (id) ON DELETE CASCADE, 
	FOREIGN KEY(event_id) REFERENCES security_events (id)
);

CREATE TABLE alert_history (
	id INTEGER NOT NULL, 
	alert_id INTEGER NOT NULL, 
	actor_id INTEGER, 
	old_status VARCHAR(20), 
	new_status VARCHAR(20) NOT NULL, 
	note TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id), 
	FOREIGN KEY(alert_id) REFERENCES alerts (id) ON DELETE CASCADE
);

CREATE TABLE "alerts" (
	id INTEGER NOT NULL, 
	event_id INTEGER NOT NULL, 
	rule_id VARCHAR(80) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	resolved_at DATETIME, 
	is_demo BOOLEAN NOT NULL, 
	subject VARCHAR(120) NOT NULL, 
	dedup_key VARCHAR(200) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_alert_dedup UNIQUE (dedup_key), 
	CONSTRAINT ck_alert_severity CHECK (severity IN ('low','medium','high','critical')), 
	CONSTRAINT ck_alert_status CHECK (status IN ('open','investigating','resolved')), 
	CONSTRAINT fk_alert_rule FOREIGN KEY(rule_id) REFERENCES detection_rules (id), 
	FOREIGN KEY(event_id) REFERENCES security_events (id)
);

CREATE TABLE "detection_rules" (
	id VARCHAR(80) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	threshold INTEGER NOT NULL, 
	window_seconds INTEGER NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	max_attempts_per_account INTEGER, 
	min_accounts INTEGER, 
	min_source_ips INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_rule_positive CHECK (threshold > 0 AND window_seconds > 0), 
	CONSTRAINT ck_rule_parameters_positive CHECK ((max_attempts_per_account IS NULL OR max_attempts_per_account > 0) AND (min_accounts IS NULL OR min_accounts > 0) AND (min_source_ips IS NULL OR min_source_ips > 0)), 
	CONSTRAINT ck_spray_parameters CHECK (id != 'AUTH-002' OR max_attempts_per_account IS NOT NULL), 
	CONSTRAINT ck_cluster_parameters CHECK (id != 'AUTH-003' OR (min_accounts IS NOT NULL AND min_source_ips IS NOT NULL))
);

CREATE TABLE rate_buckets (
	"key" VARCHAR(100) NOT NULL, 
	hits INTEGER NOT NULL, 
	expires_at DATETIME NOT NULL, 
	PRIMARY KEY ("key")
);

CREATE TABLE "security_events" (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	event_type VARCHAR(60) NOT NULL, 
	source_ip VARCHAR(45) NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	metadata_json JSON NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_event_severity CHECK (severity IN ('low','medium','high','critical')), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE sessions (
	id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	csrf_token VARCHAR(64) NOT NULL, 
	user_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_seen_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (token_hash)
);

CREATE TABLE "users" (
	id INTEGER NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_user_role CHECK (role IN ('admin','analyst'))
);

CREATE INDEX ix_alert_filter ON alerts (is_demo, status, created_at);

CREATE INDEX ix_alert_history_alert_id ON alert_history (alert_id);

CREATE INDEX ix_event_detection ON security_events (is_demo, event_type, occurred_at);

CREATE INDEX ix_event_ip_time ON security_events (source_ip, occurred_at);

CREATE INDEX ix_rate_buckets_expires_at ON rate_buckets (expires_at);

CREATE INDEX ix_security_events_event_type ON security_events (event_type);

CREATE INDEX ix_security_events_is_demo ON security_events (is_demo);

CREATE INDEX ix_security_events_occurred_at ON security_events (occurred_at);

CREATE INDEX ix_security_events_source_ip ON security_events (source_ip);

CREATE INDEX ix_sessions_expires_at ON sessions (expires_at);

CREATE INDEX ix_sessions_user_id ON sessions (user_id);

CREATE UNIQUE INDEX ix_users_username ON users (username);
