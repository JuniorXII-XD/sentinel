from datetime import datetime, timezone
from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    JSON,
    Boolean,
    CheckConstraint,
    Index,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def utcnow():
    # All DB timestamps are naive UTC for identical SQLite/PostgreSQL semantics.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin','analyst')", name="ck_user_role"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    user: Mapped[User] = relationship(back_populates="sessions")


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_event_detection", "is_demo", "event_type", "occurred_at"),
        Index("ix_event_ip_time", "source_ip", "occurred_at"),
        CheckConstraint(
            "severity IN ('low','medium','high','critical')", name="ck_event_severity"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    source_ip: Mapped[str] = mapped_column(String(45), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    severity: Mapped[str] = mapped_column(String(20), default="low")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class DetectionRule(Base):
    __tablename__ = "detection_rules"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(20))
    threshold: Mapped[int] = mapped_column(default=1)
    window_seconds: Mapped[int] = mapped_column(default=300)
    max_attempts_per_account: Mapped[int | None] = mapped_column(nullable=True)
    min_accounts: Mapped[int | None] = mapped_column(nullable=True)
    min_source_ips: Mapped[int | None] = mapped_column(nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (
        CheckConstraint(
            "threshold > 0 AND window_seconds > 0", name="ck_rule_positive"
        ),
        CheckConstraint(
            "(max_attempts_per_account IS NULL OR max_attempts_per_account > 0) AND "
            "(min_accounts IS NULL OR min_accounts > 0) AND "
            "(min_source_ips IS NULL OR min_source_ips > 0)",
            name="ck_rule_parameters_positive",
        ),
        CheckConstraint(
            "id != 'AUTH-002' OR max_attempts_per_account IS NOT NULL",
            name="ck_spray_parameters",
        ),
        CheckConstraint(
            "id != 'AUTH-003' OR (min_accounts IS NOT NULL AND min_source_ips IS NOT NULL)",
            name="ck_cluster_parameters",
        ),
    )


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','investigating','resolved')", name="ck_alert_status"
        ),
        CheckConstraint(
            "severity IN ('low','medium','high','critical')", name="ck_alert_severity"
        ),
        Index("ix_alert_filter", "is_demo", "status", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("security_events.id"))
    rule_id: Mapped[str] = mapped_column(ForeignKey("detection_rules.id"))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="open")
    description: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    subject: Mapped[str] = mapped_column(String(120), default="legacy")
    dedup_key: Mapped[str] = mapped_column(String(200), unique=True)
    evidence: Mapped[list["AlertEvidence"]] = relationship(cascade="all, delete-orphan")
    history: Mapped[list["AlertHistory"]] = relationship(
        cascade="all, delete-orphan", order_by="AlertHistory.id"
    )


class AlertEvidence(Base):
    __tablename__ = "alert_evidence"
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("security_events.id"), primary_key=True
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    old_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    hits: Mapped[int] = mapped_column(default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
