"""Independently reconcile three seeded SKU calculations against SQL sales facts."""

import json
import math
from datetime import timedelta
from statistics import NormalDist, mean, pstdev

from bottleiq.db import SessionLocal
from bottleiq.models import InventorySnapshot, OrganizationMember, Sale, Store, User
from bottleiq.services.analytics import analyze
from sqlalchemy import func, select


def main() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "demo@bottleiq.local"))
        if not user:
            raise SystemExit("Run make seed before verifying demo calculations")
        member = db.scalar(
            select(OrganizationMember).where(OrganizationMember.user_id == user.id)
        )
        store = db.scalar(
            select(Store).where(Store.organization_id == member.organization_id)
        )
        as_of = db.scalar(
            select(func.max(InventorySnapshot.snapshot_at)).where(
                InventorySnapshot.store_id == store.id
            )
        )
        metrics = analyze(db, store, as_of=as_of)
        rows = []
        for metric in metrics:
            if metric.sku not in {"BTL-0001", "BTL-0021", "BTL-0081"}:
                continue
            sales = db.execute(
                select(Sale.sold_at, func.sum(Sale.quantity))
                .where(
                    Sale.store_id == store.id,
                    Sale.product_id == metric.product_id,
                    Sale.sold_at >= as_of - timedelta(days=60),
                    Sale.sold_at < as_of,
                )
                .group_by(Sale.sold_at)
            ).all()
            by_day = dict(sales)
            daily = [
                int(by_day.get(as_of - timedelta(days=i), 0)) for i in range(1, 61)
            ]
            average, sigma = mean(daily), pstdev(daily)
            safety = (
                NormalDist().inv_cdf(0.95) * sigma * math.sqrt(metric.lead_time_days)
            )
            target = average * (metric.lead_time_days + 21) + safety
            cases = (
                math.ceil(
                    max(0, target - metric.current_quantity) / metric.units_per_case
                )
                if average
                else 0
            )
            assert math.isclose(average, metric.average_daily_demand)
            assert math.isclose(safety, metric.safety_stock)
            assert math.isclose(target, metric.target_stock)
            assert cases == metric.recommended_cases
            rows.append(
                {
                    "sku": metric.sku,
                    "product": metric.product_name,
                    "as_of": str(as_of),
                    "on_hand": metric.current_quantity,
                    "daily_demand": average,
                    "daily_std": sigma,
                    "lead_days": metric.lead_time_days,
                    "safety_stock": safety,
                    "reorder_point": average * metric.lead_time_days + safety,
                    "target_stock": target,
                    "case_pack": metric.units_per_case,
                    "cases": cases,
                    "units": cases * metric.units_per_case,
                    "unit_cost": metric.unit_cost,
                    "order_cost": metric.estimated_cost,
                    "inventory_value": metric.inventory_value,
                    "status": metric.status,
                    "verified": True,
                }
            )
        if len(rows) != 3:
            raise AssertionError("Expected the complete 96-product demo")
        print(json.dumps(sorted(rows, key=lambda row: row["sku"]), indent=2))


if __name__ == "__main__":
    main()
