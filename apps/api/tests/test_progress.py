from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bottleiq.auth import passwords
from bottleiq.models import (
    InventorySnapshot,
    Organization,
    OrganizationMember,
    Product,
    ProgressBaseline,
    Sale,
    Store,
    User,
)
from bottleiq.services.progress import (
    TrackingExists,
    progress_report,
    start_tracking,
)

TODAY = date(2026, 9, 20)


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


def seed(db, store, *, days: int, cost: str | None = "6", count_on: date | None = None) -> None:
    """One product selling 2 units a day at $10 for `days` days before TODAY."""
    product = Product(organization_id=store.organization_id, sku="001", product_name="Test")
    db.add(product)
    db.flush()
    db.add(
        InventorySnapshot(
            organization_id=store.organization_id,
            store_id=store.id,
            product_id=product.id,
            snapshot_at=count_on or TODAY - timedelta(days=days),
            quantity_on_hand=40,
            unit_cost=None if cost is None else Decimal(cost),
            retail_price=Decimal("10"),
            source_key="count",
            content_hash="count",
        )
    )
    for n in range(days):
        db.add(
            Sale(
                organization_id=store.organization_id,
                store_id=store.id,
                product_id=product.id,
                sold_at=TODAY - timedelta(days=days - n),
                quantity=2,
                gross_revenue=Decimal("20"),
                unit_price=Decimal("10"),
                source_key=f"sale-{n}",
                content_hash="sale",
            )
        )
    db.commit()


def test_baseline_is_frozen_as_of_the_start_date(db, store):
    seed(db, store, days=120)
    start_tracking(db, store, owner_id(db), TODAY - timedelta(days=30), today=TODAY)
    report = progress_report(db, store, today=TODAY)
    metrics = report["baseline"]["metrics"]
    assert report["baseline"]["started_on"] == TODAY - timedelta(days=30)
    assert metrics["inventory_value"] == 240
    assert metrics["revenue_90"] == 1800
    assert metrics["gross_profit_90"] == 720
    db.scalar(select(InventorySnapshot)).unit_cost = Decimal("9")
    db.commit()
    assert progress_report(db, store, today=TODAY)["baseline"]["metrics"] == metrics


def test_start_date_must_be_counted_and_not_in_the_future(db, store):
    seed(db, store, days=30)
    with pytest.raises(ValueError, match="future"):
        start_tracking(db, store, owner_id(db), TODAY + timedelta(days=1), today=TODAY)
    with pytest.raises(
        ValueError, match="Import an inventory count dated on or before Aug 20, 2026"
    ):
        start_tracking(db, store, owner_id(db), TODAY - timedelta(days=31), today=TODAY)
    start_tracking(db, store, owner_id(db), None, today=TODAY)
    with pytest.raises(TrackingExists):
        start_tracking(db, store, owner_id(db), None, today=TODAY)


def test_comparison_waits_for_a_week_of_data(db, store):
    seed(db, store, days=60)
    start_tracking(db, store, owner_id(db), TODAY - timedelta(days=3), today=TODAY)
    comparison = progress_report(db, store, today=TODAY)["comparison"]
    assert (comparison["kind"], comparison["days_tracked"]) == ("too_early", 3)


def test_short_history_compares_30_day_averages(db, store):
    seed(db, store, days=120)
    start_tracking(db, store, owner_id(db), TODAY - timedelta(days=30), today=TODAY)
    comparison = progress_report(db, store, today=TODAY)["comparison"]
    assert (comparison["kind"], comparison["basis"]) == ("before_after", "per_30_days")
    assert comparison["since"]["revenue"] == comparison["before"]["revenue"] == 600
    assert comparison["since"]["gross_profit"] == comparison["before"]["gross_profit"] == 240
    assert comparison["before"]["days"] == 90


def test_no_sales_before_the_start_date_cannot_be_compared(db, store):
    seed(db, store, days=20)
    start_tracking(db, store, owner_id(db), TODAY - timedelta(days=20), today=TODAY)
    assert progress_report(db, store, today=TODAY)["comparison"]["kind"] == "no_history"


def test_a_year_of_history_compares_the_same_dates_last_year(db, store):
    seed(db, store, days=400)
    start_tracking(db, store, owner_id(db), TODAY - timedelta(days=30), today=TODAY)
    comparison = progress_report(db, store, today=TODAY)["comparison"]
    assert (comparison["kind"], comparison["basis"]) == ("year_over_year", "total")
    assert comparison["before"]["start"] == date(2025, 8, 21)
    assert comparison["since"]["revenue"] == comparison["before"]["revenue"] == 600


def test_months_cover_complete_history_with_last_year(db, store):
    seed(db, store, days=400)
    start_tracking(db, store, owner_id(db), TODAY - timedelta(days=30), today=TODAY)
    months = progress_report(db, store, today=TODAY)["months"]
    assert [m["month"] for m in months][0] == "2025-10" and len(months) == 12
    current = months[-1]
    assert (current["month"], current["month_to_date"], current["days"]) == ("2026-09", True, 19)
    assert current["revenue"] == current["last_year"]["revenue"] == 380
    assert months[0]["revenue"] == 620 and months[0]["last_year"] is None


def test_revenue_without_a_cost_is_kept_out_of_profit(db, store):
    seed(db, store, days=60, cost=None)
    start_tracking(db, store, owner_id(db), TODAY - timedelta(days=30), today=TODAY)
    current = progress_report(db, store, today=TODAY)["months"][-1]
    assert current["gross_profit"] == 0
    assert current["revenue_without_cost"] == current["revenue"] == 380


def test_owner_can_start_read_and_restart_tracking(client, db, store):
    seed(db, store, days=30)
    params = {"store_id": store.id}
    client.cookies.clear()
    assert client.get("/progress", params=params).status_code == 401
    client.post("/auth/login", json={"email": "owner@example.com", "password": "test-password-123"})
    early = client.post("/progress", json={**params, "started_on": "2020-01-01"})
    assert early.status_code == 422 and "inventory count" in early.json()["detail"]
    started = client.post("/progress", json=params)
    assert started.status_code == 201
    assert started.json()["baseline"]["metrics"]["product_count"] == 1
    assert client.post("/progress", json=params).status_code == 409
    assert client.get("/progress", params=params).json()["baseline"] is not None
    assert client.delete("/progress", params=params).status_code == 204
    assert client.get("/progress", params=params).json()["baseline"] is None


def test_viewers_can_read_but_not_change_tracking(client, db, store):
    seed(db, store, days=30)
    viewer = User(
        email="viewer@example.com",
        name="Viewer",
        password_hash=passwords.hash("test-password-123"),
    )
    db.add(viewer)
    db.flush()
    db.add(
        OrganizationMember(organization_id=store.organization_id, user_id=viewer.id, role="viewer")
    )
    db.commit()
    client.post(
        "/auth/login", json={"email": "viewer@example.com", "password": "test-password-123"}
    )
    params = {"store_id": store.id}
    assert client.get("/progress", params=params).status_code == 200
    assert client.post("/progress", json=params).status_code == 403
    assert client.delete("/progress", params=params).status_code == 403


def test_other_tenant_progress_is_hidden(client, db):
    org = Organization(name="Other")
    db.add(org)
    db.flush()
    other = Store(organization_id=org.id, name="Other shop")
    db.add(other)
    db.commit()
    assert client.get("/progress", params={"store_id": other.id}).status_code == 404
    assert client.post("/progress", json={"store_id": other.id}).status_code == 404
    assert client.delete("/progress", params={"store_id": other.id}).status_code == 404
