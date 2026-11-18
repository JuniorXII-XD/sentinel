from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models import User, Session, DetectionRule
from ..schemas import NewUser, UserChange, RuleChange
from ..dependencies import admin, principal, source_ip
from ..security import hash_password
from ..services.events import record_event
from ..config import get_settings
from .auth import public_user

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("")
def settings(user=Depends(principal), db=Depends(get_db)):
    cfg = get_settings()
    return {
        "environment": cfg.environment,
        "demo_enabled": cfg.demo_enabled and cfg.environment == "development",
        "timezone": cfg.timezone,
        "work_start": cfg.work_start,
        "work_end": cfg.work_end,
        "session_hours": cfg.session_hours,
        "idle_minutes": cfg.idle_minutes,
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "enabled": r.enabled,
                "severity": r.severity,
                "threshold": r.threshold,
                "window_seconds": r.window_seconds,
                "max_attempts_per_account": r.max_attempts_per_account,
                "min_accounts": r.min_accounts,
                "min_source_ips": r.min_source_ips,
            }
            for r in db.scalars(select(DetectionRule).order_by(DetectionRule.id))
        ],
    }


@router.get("/users")
def users(user=Depends(admin), db=Depends(get_db)):
    return [
        public_user(x) for x in db.scalars(select(User).order_by(User.id).limit(500))
    ]


@router.post("/users", status_code=201)
def add_user(
    payload: NewUser, request: Request, user=Depends(admin), db=Depends(get_db)
):
    new = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(new)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username already exists")
    record_event(
        db,
        "privilege_changed",
        source_ip(request),
        user.id,
        {"target_user_id": new.id, "new_role": new.role, "reason": "account_created"},
    )
    db.commit()
    return public_user(new)


@router.patch("/users/{user_id}")
def change_user(
    user_id: int,
    payload: UserChange,
    request: Request,
    actor=Depends(admin),
    db=Depends(get_db),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    # Keeping self changes forbidden ensures at least one active administrator survives.
    if target.id == actor.id:
        raise HTTPException(400, "You cannot change your own role or disable yourself")
    old_role, old_active = target.role, target.is_active
    target.role, target.is_active = payload.role, payload.is_active
    db.execute(delete(Session).where(Session.user_id == target.id))
    record_event(
        db,
        "privilege_changed",
        source_ip(request),
        actor.id,
        {
            "target_user_id": target.id,
            "old_role": old_role,
            "new_role": target.role,
            "old_active": old_active,
            "new_active": target.is_active,
        },
    )
    db.commit()
    return public_user(target)


@router.patch("/rules/{rule_id}")
def change_rule(
    rule_id: str,
    payload: RuleChange,
    request: Request,
    actor=Depends(admin),
    db=Depends(get_db),
):
    rule = db.get(DetectionRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    rule.enabled = payload.enabled
    record_event(
        db,
        "rule_changed",
        source_ip(request),
        actor.id,
        {"rule_id": rule.id, "enabled": rule.enabled},
    )
    db.commit()
    return {"id": rule.id, "enabled": rule.enabled}
