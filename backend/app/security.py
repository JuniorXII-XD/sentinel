import hashlib
import secrets
from datetime import timedelta
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from sqlalchemy import case
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .models import RateBucket, utcnow

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, type=Type.ID)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def hash_password(password):
    return hasher.hash(password)


def verify_password(password, password_hash):
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def rate_hit(db, scope, identity, limit, seconds):
    """Atomic DB-backed fixed-window counter, shared by workers; no raw account keys."""
    now = utcnow()
    key = scope + ":" + digest(identity)
    ins = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    statement = ins(RateBucket).values(
        key=key, hits=1, expires_at=now + timedelta(seconds=seconds)
    )
    statement = statement.on_conflict_do_update(
        index_elements=["key"],
        set_={
            "hits": case((RateBucket.expires_at <= now, 1), else_=RateBucket.hits + 1),
            "expires_at": case(
                (RateBucket.expires_at <= now, now + timedelta(seconds=seconds)),
                else_=RateBucket.expires_at,
            ),
        },
    ).returning(RateBucket.hits)
    hits = db.execute(statement).scalar_one()
    return hits <= limit
