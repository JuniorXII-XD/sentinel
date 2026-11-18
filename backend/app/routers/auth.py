import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, delete
from ..database import get_db
from ..models import User, Session, utcnow
from ..schemas import Login
from ..security import (
    hash_password,
    verify_password,
    digest,
    rate_hit,
    hasher,
    DUMMY_HASH,
)
from ..config import get_settings
from ..dependencies import principal, session_probe, source_ip
from ..services.events import record_event

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def public_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
    }


@router.post("/login")
def login(payload: Login, request: Request, response: Response, db=Depends(get_db)):
    cfg, ip = get_settings(), source_ip(request)
    ip_ok = rate_hit(db, "login-ip", ip, 20, 300)
    # Username cannot contain ':', so the pair has an unambiguous encoding.
    pair = f"{payload.username}:{ip}"
    account_ok = rate_hit(db, "login-account-ip", pair, 8, 300)
    if not ip_ok or not account_ok:
        if rate_hit(db, "lock-audit", pair, 1, 300):
            record_event(
                db,
                "suspicious_activity",
                ip,
                metadata={"account": payload.username, "reason": "login_rate_limit"},
            )
        db.commit()
        raise HTTPException(
            429,
            "Too many attempts. Try again in five minutes.",
            headers={"Retry-After": "300"},
        )
    user = db.scalar(select(User).where(User.username == payload.username))
    valid = verify_password(
        payload.password, user.password_hash if user else DUMMY_HASH
    )
    if not user or not valid or not user.is_active:
        record_event(
            db,
            "login_failed",
            ip,
            user.id if user else None,
            {"account": payload.username},
        )
        db.commit()
        raise HTTPException(401, "Invalid username or password")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    previous = request.cookies.get(cfg.cookie_name)
    if previous:
        db.execute(delete(Session).where(Session.token_hash == digest(previous)))
    db.execute(delete(Session).where(Session.expires_at < utcnow()))
    raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    session = Session(
        token_hash=digest(raw),
        csrf_token=csrf,
        user_id=user.id,
        expires_at=utcnow() + timedelta(hours=cfg.session_hours),
    )
    db.add(session)
    record_event(db, "login_success", ip, user.id, {"account": user.username})
    db.commit()
    response.set_cookie(
        cfg.cookie_name,
        raw,
        max_age=cfg.session_hours * 3600,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="strict",
        path="/",
    )
    return {"user": public_user(user), "csrf_token": csrf}


@router.get("/me")
def me(request: Request, user=Depends(session_probe)):
    cfg = get_settings()
    return {
        "user": public_user(user),
        "csrf_token": request.state.session.csrf_token,
        "demo_enabled": cfg.demo_enabled and cfg.environment == "development",
    }


@router.post("/logout", status_code=204)
def logout(
    request: Request, response: Response, user=Depends(principal), db=Depends(get_db)
):
    db.delete(request.state.session)
    record_event(db, "logout", source_ip(request), user.id)
    db.commit()
    cfg = get_settings()
    response.delete_cookie(
        cfg.cookie_name,
        path="/",
        secure=cfg.cookie_secure,
        httponly=True,
        samesite="strict",
    )
