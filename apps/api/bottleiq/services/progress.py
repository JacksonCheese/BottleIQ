"""Store progress since tracking began.

The Day 1 baseline is frozen when tracking starts so later imports cannot move it.
Current numbers and sales comparisons are calculated live from the store's data.
"""

from datetime import date, datetime, timedelta
from functools import partial
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bottleiq.models import InventorySnapshot, ProgressBaseline, Sale, Store
from bottleiq.schemas import Metrics
from bottleiq.services.analytics import analyze

MINIMUM_DAYS = 7
BEFORE_WINDOW_DAYS = 90
MONTHS_SHOWN = 12


class TrackingExists(Exception):
    """The store already has a baseline; restart tracking to choose a new start date."""


def store_today(store: Store) -> date:
    return datetime.now(ZoneInfo(store.timezone)).date()


def one_year_earlier(day: date) -> date:
    try:
        return day.replace(year=day.year - 1)
    except ValueError:  # February 29
        return day.replace(year=day.year - 1, day=28)


def headline(metrics: list[Metrics]) -> dict:
    """Dashboard headline numbers; slow value excludes dead value so the two add up."""
    snapshot = max((m.snapshot_at for m in metrics if m.snapshot_at), default=None)
    return {
        "inventory_value": round(sum(m.inventory_value or 0 for m in metrics), 2),
        "dead_value": round(sum(m.inventory_value or 0 for m in metrics if m.dead), 2),
        "slow_value": round(
            sum(m.inventory_value or 0 for m in metrics if m.slow and not m.dead), 2
        ),
        "stockout_risks": sum(m.stockout for m in metrics),
        "product_count": len(metrics),
        "missing_cost_count": sum(m.unit_cost is None for m in metrics),
        "revenue_90": round(sum(m.revenue_90 for m in metrics), 2),
        "gross_profit_90": round(sum(m.gross_profit or 0 for m in metrics), 2),
        "snapshot_at": snapshot.isoformat() if snapshot else None,
    }


def baseline_for(db: Session, store: Store) -> ProgressBaseline | None:
    return db.scalar(
        select(ProgressBaseline).where(
            ProgressBaseline.store_id == store.id,
            ProgressBaseline.organization_id == store.organization_id,
        )
    )


def start_tracking(
    db: Session,
    store: Store,
    user_id: str,
    started_on: date | None = None,
    today: date | None = None,
) -> ProgressBaseline:
    today = today or store_today(store)
    started_on = started_on or today
    if started_on > today:
        raise ValueError("The start date cannot be in the future.")
    counted = db.scalar(
        select(InventorySnapshot.id)
        .where(
            InventorySnapshot.store_id == store.id,
            InventorySnapshot.organization_id == store.organization_id,
            InventorySnapshot.snapshot_at <= started_on,
        )
        .limit(1)
    )
    if counted is None:
        raise ValueError(
            "Import an inventory count dated on or before "
            f"{started_on:%b} {started_on.day}, {started_on.year} "
            "before starting from this date."
        )
    if baseline_for(db, store):
        raise TrackingExists
    baseline = ProgressBaseline(
        organization_id=store.organization_id,
        store_id=store.id,
        started_on=started_on,
        created_by_user_id=user_id,
        metrics=headline(analyze(db, store, as_of=started_on)),
    )
    db.add(baseline)
    db.commit()
    return baseline


def stop_tracking(db: Session, store: Store) -> None:
    baseline = baseline_for(db, store)
    if baseline:
        db.delete(baseline)
        db.commit()


def latest_costs(db: Session, store: Store, today: date) -> dict[str, float]:
    """Latest known unit cost per product, matching the estimated-COGS definition."""
    costs: dict[str, float] = {}
    for product_id, cost in db.execute(
        select(InventorySnapshot.product_id, InventorySnapshot.unit_cost)
        .where(
            InventorySnapshot.store_id == store.id,
            InventorySnapshot.organization_id == store.organization_id,
            InventorySnapshot.unit_cost.is_not(None),
            InventorySnapshot.snapshot_at <= today,
        )
        .order_by(InventorySnapshot.snapshot_at)
    ):
        costs[product_id] = float(cost)
    return costs


def totals(
    db: Session,
    store: Store,
    start: date,
    end: date,
    costs: dict[str, float],
    scale: float = 1.0,
) -> dict:
    """Sales for complete days in [start, end); profit only where a cost is known."""
    revenue = profit = uncosted = 0.0
    for product_id, units, sold in db.execute(
        select(Sale.product_id, func.sum(Sale.quantity), func.sum(Sale.gross_revenue))
        .where(
            Sale.store_id == store.id,
            Sale.organization_id == store.organization_id,
            Sale.sold_at >= start,
            Sale.sold_at < end,
        )
        .group_by(Sale.product_id)
    ):
        sold = float(sold or 0)
        revenue += sold
        if product_id in costs:
            profit += sold - (units or 0) * costs[product_id]
        else:
            uncosted += sold
    return {
        "start": start,
        "end": end - timedelta(days=1),
        "days": (end - start).days,
        "revenue": round(revenue * scale, 2),
        "gross_profit": round(profit * scale, 2),
        "revenue_without_cost": round(uncosted * scale, 2),
    }


def comparison(period: partial, started_on: date, today: date, first_sale: date | None) -> dict:
    days = (today - started_on).days
    result: dict = {
        "kind": "too_early",
        "days_tracked": days,
        "basis": "total",
        "since": None,
        "before": None,
    }
    if days < MINIMUM_DAYS:
        return result
    last_year = one_year_earlier(started_on)
    if first_sale is not None and first_sale <= last_year:
        return {
            **result,
            "kind": "year_over_year",
            "since": period(started_on, today),
            "before": period(last_year, one_year_earlier(today)),
        }
    before_start = (
        max(started_on - timedelta(days=BEFORE_WINDOW_DAYS), first_sale)
        if first_sale
        else started_on
    )
    before_days = (started_on - before_start).days
    if before_days < MINIMUM_DAYS:
        return {**result, "kind": "no_history"}
    # Different-length windows are compared as 30-day averages; seasonality still applies.
    return {
        **result,
        "kind": "before_after",
        "basis": "per_30_days",
        "since": period(started_on, today, scale=30 / days),
        "before": period(before_start, started_on, scale=30 / before_days),
    }


def months(period: partial, today: date, first_sale: date | None) -> list[dict]:
    """Calendar months fully covered by sales history, ending with month-to-date."""
    rows: list[dict] = []
    if first_sale is None:
        return rows
    for offset in range(MONTHS_SHOWN - 1, -1, -1):
        year, month = divmod(today.year * 12 + today.month - 1 - offset, 12)
        start = date(year, month + 1, 1)
        next_month = (start + timedelta(days=32)).replace(day=1)
        end = min(next_month, today)
        if end <= start or first_sale > start:
            continue
        last_year_start = one_year_earlier(start)
        rows.append(
            {
                "month": start.strftime("%Y-%m"),
                "month_to_date": end < next_month,
                **period(start, end),
                "last_year": period(last_year_start, one_year_earlier(end))
                if first_sale <= last_year_start
                else None,
            }
        )
    return rows


def progress_report(db: Session, store: Store, today: date | None = None) -> dict:
    today = today or store_today(store)
    current = headline(analyze(db, store, as_of=today))
    baseline = baseline_for(db, store)
    if baseline is None:
        return {
            "today": today,
            "baseline": None,
            "current": current,
            "comparison": None,
            "months": [],
        }
    period = partial(totals, db, store, costs=latest_costs(db, store, today))
    first_sale = db.scalar(
        select(func.min(Sale.sold_at)).where(
            Sale.store_id == store.id, Sale.organization_id == store.organization_id
        )
    )
    return {
        "today": today,
        "baseline": {
            "started_on": baseline.started_on,
            "created_at": baseline.created_at,
            "metrics": baseline.metrics,
        },
        "current": current,
        "comparison": comparison(period, baseline.started_on, today, first_sale),
        "months": months(period, today, first_sale),
    }
