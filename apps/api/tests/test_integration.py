from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from bottleiq.models import IncomingStock, InventorySnapshot
from bottleiq.schemas import AnalysisOptions, OrderEdit, OrderInput, OrderLineEdit
from bottleiq.seed import seed_demo
from bottleiq.services.analytics import alerts_for, analyze
from bottleiq.services.orders import create_order, edit_order, export_order, order_detail


def test_seed_analytics_recommendations_order(db, today):
    store = seed_demo(db, today)
    metrics = analyze(db, store, as_of=today)
    assert len(metrics) == 96
    by_sku = {m.sku: m for m in metrics}
    fast, normal, dead = by_sku["BTL-0001"], by_sku["BTL-0021"], by_sku["BTL-0081"]
    assert fast.average_daily_demand == 4
    assert fast.days_of_supply == 2
    assert fast.stockout and fast.recommended_cases == 8 and fast.estimated_cost == 1728
    assert normal.current_quantity == 70 and normal.recommended_cases == 0
    assert dead.dead and dead.slow and dead.recommended_units == 0
    assert by_sku["BTL-0080"].unit_cost is None
    assert by_sku["BTL-0080"].recommended_cases == 0
    assert by_sku["BTL-0079"].vendor_id is None
    assert "missing vendor" in by_sku["BTL-0079"].blockers
    assert any(a.title == "Unusual demand" for a in alerts_for(metrics))
    # Creation uses today's date; fixed as_of is intentionally today's CI date-independent seed below.
    from datetime import date

    shift = date.today() - today
    if shift.days:
        from bottleiq.models import Sale

        for row in db.scalars(select(Sale).where(Sale.store_id == store.id)):
            row.sold_at += shift
        for row in db.scalars(
            select(InventorySnapshot).where(InventorySnapshot.store_id == store.id)
        ):
            row.snapshot_at += shift
        db.commit()
    order = create_order(db, store, OrderInput(store_id=store.id, vendor_id=fast.vendor_id))
    detail = order_detail(db, order)
    assert detail["estimated_total_cost"] == pytest.approx(
        sum(item["line_total"] for item in detail["lines"])
    )
    line = next(item for item in detail["lines"] if item["product_id"] == fast.product_id)
    assert line["units"] == 96
    edit_order(
        db,
        order,
        OrderEdit(
            version=order.version, lines=[OrderLineEdit(product_id=fast.product_id, cases=2)]
        ),
    )
    updated = order_detail(db, order)
    assert updated["estimated_total_cost"] == pytest.approx(
        detail["estimated_total_cost"] - 1728 + 432
    )
    assert "Cedar Ridge" in export_order(updated)
    edit_order(
        db,
        order,
        OrderEdit(
            version=order.version, lines=[OrderLineEdit(product_id=fast.product_id, cases=0)]
        ),
    )
    assert fast.sku not in export_order(order_detail(db, order))


def test_stale_data_blocks_purchases(db, today):
    store = seed_demo(db, today, product_count=4)
    stale = analyze(db, store, as_of=today + timedelta(days=10))
    assert all(m.recommended_units == 0 for m in stale)
    assert all("inventory older than 7 days" in m.blockers for m in stale)
    assert all("sales export older than 7 days" in m.blockers for m in stale)


def test_missing_cost_does_not_become_free_order(db, today):
    store = seed_demo(db, today, product_count=2)
    snapshot = db.scalar(select(InventorySnapshot))
    snapshot.unit_cost = None
    db.commit()
    metric = next(m for m in analyze(db, store, as_of=today) if m.product_id == snapshot.product_id)
    assert metric.estimated_cost is None and metric.recommended_units == 0
    assert metric.inventory_value is None and metric.gross_profit is None


def test_zero_cost_holds_order(db, today):
    store = seed_demo(db, today, product_count=1)
    snapshot = db.scalar(select(InventorySnapshot))
    snapshot.unit_cost = Decimal(0)
    db.commit()
    assert analyze(db, store, as_of=today)[0].recommended_cases == 0


def test_configurable_demand_window(db, today):
    store = seed_demo(db, today, product_count=1)
    for window in (30, 60, 90):
        m = analyze(db, store, AnalysisOptions(window=window), as_of=today)[0]
        assert m.average_daily_demand == 4
        assert m.sales_30 == 120 and m.sales_90 == 360


def test_stale_order_version_rejected(db, today):
    from datetime import date

    from fastapi import HTTPException

    store = seed_demo(db, date.today(), product_count=1)
    metric = analyze(db, store)[0]
    order = create_order(db, store, OrderInput(store_id=store.id, vendor_id=metric.vendor_id))
    edit_order(db, order, OrderEdit(version=1, lines=[]))
    with pytest.raises(HTTPException) as error:
        edit_order(db, order, OrderEdit(version=1, lines=[]))
    assert error.value.status_code == 409


def test_confirmed_incoming_reduces_live_order_and_can_be_resolved(db, client):
    as_of = date.today()
    store = seed_demo(db, as_of, product_count=1)
    before = analyze(db, store)[0]
    assert before.recommended_cases == 8
    # A different organization cannot add inbound stock to the demo product.
    foreign = client.post(
        "/incoming-stock",
        json={
            "store_id": store.id,
            "product_id": before.product_id,
            "quantity_units": 72,
            "expected_at": (as_of + timedelta(days=1)).isoformat(),
        },
    )
    assert foreign.status_code == 404
    assert client.post("/auth/demo").status_code == 200
    created = client.post(
        "/incoming-stock",
        json={
            "store_id": store.id,
            "product_id": before.product_id,
            "quantity_units": 72,
            "expected_at": (as_of + timedelta(days=1)).isoformat(),
            "reference": "PO-123",
        },
    )
    assert created.status_code == 201
    assert created.json()["quantity_units"] == 72
    after = analyze(db, store)[0]
    assert after.incoming_units == 72
    assert after.inventory_position == 80
    assert after.recommended_cases == 2
    assert not after.stockout  # Tomorrow's confirmed delivery arrives before stock runs out.
    assert "72 confirmed incoming units" in after.explanation
    order = create_order(db, store, OrderInput(store_id=store.id, vendor_id=before.vendor_id))
    assert order_detail(db, order)["lines"][0]["cases"] == 2
    resolved = client.patch(f"/incoming-stock/{created.json()['id']}", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert analyze(db, store)[0].recommended_cases == 8


def test_overdue_incoming_holds_order_until_review(db):
    as_of = date.today()
    store = seed_demo(db, as_of, product_count=1)
    metric = analyze(db, store)[0]
    db.add(
        IncomingStock(
            organization_id=store.organization_id,
            store_id=store.id,
            product_id=metric.product_id,
            quantity_units=72,
            expected_at=as_of - timedelta(days=1),
        )
    )
    db.commit()
    held = analyze(db, store)[0]
    assert held.recommended_cases == 0
    assert "overdue incoming stock needs review" in held.blockers


def test_seed_can_resume_without_duplicate_facts(db, today):
    from sqlalchemy import func

    from bottleiq.models import Sale

    first = seed_demo(db, today, product_count=1)
    second = seed_demo(db, product_count=1)
    assert first.id == second.id
    assert db.scalar(select(func.count()).select_from(Sale)) == 210
