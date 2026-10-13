from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bottleiq.models import ProgressBaseline, User


def owner_id(db) -> str:
    return db.scalar(select(User.id).where(User.email == "owner@example.com"))


def test_one_baseline_per_store(db, store):
    for _ in range(2):
        db.add(
            ProgressBaseline(
                organization_id=store.organization_id,
                store_id=store.id,
                started_on=date(2026, 9, 1),
                created_by_user_id=owner_id(db),
                metrics={},
            )
        )
    with pytest.raises(IntegrityError):
        db.flush()
