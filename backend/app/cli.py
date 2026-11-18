import argparse
import getpass
import os
from sqlalchemy import select, delete
from .database import SessionLocal
from .models import User, Session, RateBucket, utcnow
from .security import hash_password
from .schemas import NewUser
from .services.events import record_event
from .services.detection import seed_rules
from .services.demo import seed_demo
from .config import get_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["create-user", "reset-password", "seed-demo", "cleanup"]
    )
    parser.add_argument("--username", default="admin")
    parser.add_argument("--role", choices=["admin", "analyst"], default="admin")
    args = parser.parse_args()
    with SessionLocal() as db:
        seed_rules(db)
        if args.command in ("create-user", "reset-password"):
            password = os.getenv("SENTINEL_BOOTSTRAP_PASSWORD") or getpass.getpass(
                "Password (12+ characters): "
            )
            payload = NewUser(username=args.username, password=password, role=args.role)
            user = db.scalar(select(User).where(User.username == payload.username))
            if args.command == "create-user":
                if user:
                    raise SystemExit("Username already exists")
                user = User(
                    username=payload.username,
                    password_hash=hash_password(password),
                    role=payload.role,
                )
                db.add(user)
                db.flush()
                reason = "cli_account_created"
            else:
                if not user:
                    raise SystemExit("User not found")
                user.password_hash = hash_password(password)
                db.execute(delete(Session).where(Session.user_id == user.id))
                reason = "cli_password_reset"
            record_event(
                db,
                "privilege_changed",
                "127.0.0.1",
                user.id,
                {"reason": reason, "new_role": user.role},
            )
            print("Account updated. Password was not logged.")
        elif args.command == "seed-demo":
            cfg = get_settings()
            if cfg.environment != "development" or not cfg.demo_enabled:
                raise SystemExit("Demo requires development and DEMO_ENABLED=true")
            user = db.scalar(
                select(User).where(
                    User.username == args.username,
                    User.role == "admin",
                    User.is_active.is_(True),
                )
            )
            if not user:
                raise SystemExit("Active administrator required")
            print(
                "Synthetic data created"
                if seed_demo(db, user.id)
                else "Demo already exists"
            )
        else:
            db.execute(delete(Session).where(Session.expires_at < utcnow()))
            db.execute(delete(RateBucket).where(RateBucket.expires_at < utcnow()))
            print("Expired sessions and counters cleaned")
        db.commit()


if __name__ == "__main__":
    main()
