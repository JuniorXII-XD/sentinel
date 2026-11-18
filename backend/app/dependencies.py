import secrets
from datetime import timedelta
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, update
from .database import get_db
from .models import Session, utcnow
from .config import get_settings
from .security import digest, rate_hit
from .services.events import record_event


def source_ip(request):
    # Never accept arbitrary X-Forwarded-For. Configure proxy trust at the ASGI server.
    return request.client.host if request.client else "unknown"


SESSION_TOUCH_SECONDS = 30


def authenticate(request: Request, db, *, audit_denial: bool):
    cfg = get_settings()
    raw = request.cookies.get(cfg.cookie_name, "")
    session = (
        db.scalar(select(Session).where(Session.token_hash == digest(raw)))
        if raw and len(raw) <= 128
        else None
    )
    now = utcnow()
    if (
        not session
        or session.expires_at <= now
        or session.last_seen_at <= now - timedelta(minutes=cfg.idle_minutes)
        or not session.user.is_active
    ):
        if audit_denial:
            if rate_hit(db, "unauth-audit", source_ip(request), 5, 60):
                record_event(
                    db,
                    "unauthorized_access",
                    source_ip(request),
                    metadata={
                        "path": request.url.path,
                        "reason": "authentication_required",
                    },
                )
            db.commit()
        raise HTTPException(401, "Authentication required")
    if not rate_hit(db, "api", str(session.user_id), 240, 60):
        db.commit()
        raise HTTPException(
            429, "Request limit exceeded", headers={"Retry-After": "60"}
        )
    if request.method not in ("GET", "HEAD", "OPTIONS") and not secrets.compare_digest(
        request.headers.get("x-csrf-token", ""), session.csrf_token
    ):
        db.commit()
        raise HTTPException(403, "CSRF validation failed")
    # Conditional update avoids one session-row write per request and prevents
    # an older concurrent request from moving activity backwards. The API rate
    # bucket still needs a DB write/commit on every authenticated request.
    cutoff = now - timedelta(seconds=SESSION_TOUCH_SECONDS)
    if session.last_seen_at <= cutoff:
        db.execute(
            update(Session)
            .where(Session.id == session.id, Session.last_seen_at <= cutoff)
            .values(last_seen_at=now)
        )
    db.commit()
    request.state.session = session
    return session.user


def principal(request: Request, db=Depends(get_db)):
    return authenticate(request, db, audit_denial=True)


def session_probe(request: Request, db=Depends(get_db)):
    # Missing/expired cookies are expected during boot and logout, not incidents.
    # Keep 401 and all validity checks; only suppress the denial audit for /me.
    return authenticate(request, db, audit_denial=False)


def admin(request: Request, user=Depends(principal), db=Depends(get_db)):
    if user.role != "admin":
        record_event(
            db,
            "unauthorized_access",
            source_ip(request),
            user.id,
            {"path": request.url.path, "reason": "admin_required"},
        )
        db.commit()
        raise HTTPException(403, "Administrator role required")
    return user
