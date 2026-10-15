"""Run daily from the hosting scheduler to bound shared throttle storage."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from bottleiq.db import SessionLocal
from bottleiq.models import AuthRateLimit


def main() -> None:
    cutoff = datetime.now(UTC) - timedelta(days=2)
    with SessionLocal() as db:
        db.execute(delete(AuthRateLimit).where(AuthRateLimit.window_start < cutoff))
        db.commit()
    print("Pruned expired authentication throttle rows")


if __name__ == "__main__":
    main()
