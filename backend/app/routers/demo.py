from fastapi import APIRouter, Depends, HTTPException, Request
from ..database import get_db
from ..config import get_settings
from ..dependencies import admin, source_ip
from ..schemas import DemoEvent
from ..security import rate_hit
from ..services.events import record_event
from ..services.demo import seed_demo

router = APIRouter(prefix="/api/demo", tags=["Development only"])


def demo_guard(request: Request, actor=Depends(admin), db=Depends(get_db)):
    cfg = get_settings()
    if cfg.environment != "development" or not cfg.demo_enabled:
        raise HTTPException(404, "Not found")
    if not rate_hit(db, "demo", str(actor.id), 60, 60):
        db.commit()
        raise HTTPException(429, "Demo rate limit", headers={"Retry-After": "60"})
    return actor


@router.post("/events", status_code=201)
def demo_event(payload: DemoEvent, actor=Depends(demo_guard), db=Depends(get_db)):
    event = record_event(
        db,
        payload.event_type,
        payload.source_ip,
        metadata={"account": payload.account, "source": "demo"},
        is_demo=True,
    )
    db.commit()
    return {"id": event.id, "is_demo": True}


@router.post("/seed")
def demo_seed(request: Request, actor=Depends(demo_guard), db=Depends(get_db)):
    seeded = seed_demo(db, actor.id)
    if seeded:
        record_event(
            db,
            "demo_seeded",
            source_ip(request),
            actor.id,
            {"source": "demo"},
            is_demo=True,
        )
    db.commit()
    return {
        "created": seeded,
        "message": "Synthetic scenarios created"
        if seeded
        else "Demo dataset already exists",
    }
