"""Database-backed account throttle shared by all API workers."""

import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from bottleiq.auth import as_utc
from bottleiq.models import AuthRateLimit


def limit_auth(db: Session, purpose: str, email: str, *, limit: int, seconds: int) -> None:
    key_hash = hashlib.sha256(f"{purpose}:{email.lower()}".encode()).hexdigest()
    if db.bind and db.bind.dialect.name == "postgresql":
        lock_key = int.from_bytes(bytes.fromhex(key_hash[:16]), "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    now = datetime.now(UTC)
    entry = db.scalar(
        select(AuthRateLimit).where(AuthRateLimit.key_hash == key_hash).with_for_update()
    )
    if entry is None:
        entry = AuthRateLimit(key_hash=key_hash, window_start=now, hit_count=1)
        db.add(entry)
    elif as_utc(entry.window_start) + timedelta(seconds=seconds) <= now:
        entry.window_start = now
        entry.hit_count = 1
    else:
        entry.hit_count += 1
    db.commit()
    if entry.hit_count > limit:
        raise HTTPException(
            429,
            "Too many attempts for this account. Try again later.",
            headers={"Retry-After": str(seconds)},
        )
