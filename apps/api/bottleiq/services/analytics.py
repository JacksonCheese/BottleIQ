from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import polars as pl
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bottleiq.models import (
    IncomingStock,
    InventorySnapshot,
    Product,
    ReorderRecommendation,
    Sale,
    Store,
    Vendor,
)
from bottleiq.schemas import Alert, AnalysisOptions, Metrics
from bottleiq.services.calculations import (
    abc_classes,
    demand_metrics,
    stockout_before_replenishment,
)


def analyze(
    db: Session, store: Store, options: AnalysisOptions | None = None, as_of: date | None = None
) -> list[Metrics]:
    options = options or AnalysisOptions()
    today = as_of or datetime.now(ZoneInfo(store.timezone)).date()
    org = store.organization_id
    horizon = max(90, options.dead_days, options.window)
    start = today - timedelta(days=horizon)
    products = db.scalars(
        select(Product)
        .where(Product.organization_id == org, Product.active.is_(True))
        .order_by(Product.product_name)
    ).all()
    vendors = {v.id: v for v in db.scalars(select(Vendor).where(Vendor.organization_id == org))}
    snapshots = db.scalars(
        select(InventorySnapshot)
        .where(
            InventorySnapshot.store_id == store.id,
            InventorySnapshot.organization_id == org,
            InventorySnapshot.snapshot_at <= today,
        )
        .order_by(InventorySnapshot.snapshot_at)
    ).all()
    latest = {s.product_id: s for s in snapshots}
    incoming_by_product: dict[str, list[IncomingStock]] = {}
    for shipment in db.scalars(
        select(IncomingStock).where(
            IncomingStock.store_id == store.id,
            IncomingStock.organization_id == org,
            IncomingStock.status == "open",
        )
    ):
        incoming_by_product.setdefault(shipment.product_id, []).append(shipment)
    first_sale = db.scalar(
        select(func.min(Sale.sold_at)).where(Sale.store_id == store.id, Sale.organization_id == org)
    )
    last_sale = db.scalar(
        select(func.max(Sale.sold_at)).where(
            Sale.store_id == store.id, Sale.organization_id == org, Sale.sold_at < today
        )
    )
    observed_days = min(options.window, (today - first_sale).days) if first_sale else 0
    sales = db.scalars(
        select(Sale).where(
            Sale.store_id == store.id,
            Sale.organization_id == org,
            Sale.sold_at >= start,
            Sale.sold_at < today,
        )
    ).all()
    totals: dict[tuple[str, date], tuple[int, float]] = {}
    if sales:
        frame = pl.DataFrame(
            {
                "product_id": [s.product_id for s in sales],
                "date": [s.sold_at for s in sales],
                "quantity": [s.quantity for s in sales],
                "revenue": [float(s.gross_revenue) for s in sales],
            }
        )
        for row in (
            frame.group_by(["product_id", "date"])
            .agg(pl.col("quantity").sum(), pl.col("revenue").sum())
            .iter_rows(named=True)
        ):
            totals[(row["product_id"], row["date"])] = (row["quantity"], row["revenue"])
    result: list[Metrics] = []
    for p in products:
        snap = latest.get(p.id)
        # Catalog is organization-wide; only show SKUs observed in this store.
        if snap is None and not any(s.product_id == p.id for s in sales):
            continue
        daily = [totals.get((p.id, start + timedelta(days=i)), (0, 0.0)) for i in range(horizon)]
        units = [d[0] for d in daily]
        vendor = vendors.get(p.default_vendor_id or "")
        lead = vendor.default_lead_time_days if vendor else 4
        hand = snap.quantity_on_hand if snap else 0
        shipments = incoming_by_product.get(p.id, [])
        overdue_incoming = any(shipment.expected_at < today for shipment in shipments)
        horizon_end = today + timedelta(days=lead + options.target_days)
        incoming_units = sum(
            shipment.quantity_units
            for shipment in shipments
            if today <= shipment.expected_at <= horizon_end
        )
        cost = float(snap.unit_cost) if snap and snap.unit_cost is not None else None
        price = float(snap.retail_price) if snap else 0.0
        demand = demand_metrics(
            units[-max(1, observed_days) :],
            hand,
            lead,
            p.units_per_case,
            options.target_days,
            options.service_level,
            incoming_units,
        )
        qty90 = sum(units[-90:])
        revenue = sum(x[1] for x in daily[-90:])
        dead = (
            sum(units[-options.dead_days :]) == 0
            and hand > 0
            and first_sale is not None
            and (today - first_sale).days >= options.dead_days
        )
        slow = hand > 0 and (demand.days is None or demand.days > options.slow_days)
        incoming_by_day: dict[int, int] = {}
        for shipment in shipments:
            days_until_arrival = (shipment.expected_at - today).days
            if 0 <= days_until_arrival <= lead:
                incoming_by_day[days_until_arrival] = (
                    incoming_by_day.get(days_until_arrival, 0) + shipment.quantity_units
                )
        risk = stockout_before_replenishment(
            hand, demand.average, demand.safety, lead, incoming_by_day
        )
        recent, baseline = sum(units[-7:]) / 7, sum(units[-35:-7]) / 28
        abnormal = baseline > 0 and recent >= 2 * baseline and recent - baseline >= 1
        blockers = []
        if cost is None or cost <= 0:
            blockers.append("missing cost")
        if vendor is None:
            blockers.append("missing vendor")
        if snap is None:
            blockers.append("missing inventory")
        elif (today - snap.snapshot_at).days > 7:
            blockers.append("inventory older than 7 days")
        if observed_days < 14:
            blockers.append("less than 14 days of sales history")
        if last_sale is None or (today - last_sale).days > 7:
            blockers.append("sales export older than 7 days")
        if overdue_incoming:
            blockers.append("overdue incoming stock needs review")
        cases = 0 if blockers else demand.cases
        status = (
            "needs_data"
            if blockers
            else "dead"
            if dead
            else "stockout"
            if risk
            else "slow"
            if slow
            else "healthy"
        )
        if blockers:
            explanation = (
                "Order held: " + ", ".join(blockers) + ". Update your data before purchasing."
            )
        elif dead:
            explanation = f"No sales in {options.dead_days} days. Do not reorder; review a markdown or return with your distributor."
        elif demand.average == 0:
            explanation = "No demand in the selected period. Do not reorder; verify sales coverage."
        elif cases:
            inbound_note = (
                f" {incoming_units} confirmed incoming units are already counted."
                if incoming_units
                else ""
            )
            explanation = f"Stock covers {demand.days:.1f} days. With a {lead}-day lead time and {options.target_days}-day replenishment target, order {cases} cases ({cases * p.units_per_case} units), including {demand.safety:.1f} units of safety stock.{inbound_note}"
        elif incoming_units:
            explanation = f"{incoming_units} confirmed incoming units due within the planning window cover the replenishment need. Check delivery timing before purchasing."
        else:
            explanation = f"Stock covers {demand.days:.1f} days, above the replenishment target. Do not reorder this week."
        inventory_value = hand * cost if cost is not None else None
        history_values = [
            s.quantity_on_hand * float(s.unit_cost)
            for s in snapshots
            if s.product_id == p.id
            and s.snapshot_at >= today - timedelta(days=90)
            and s.unit_cost is not None
        ]
        average_value = sum(history_values) / len(history_values) if history_values else 0
        gross_profit = revenue - qty90 * cost if cost is not None else None
        result.append(
            Metrics(
                product_id=p.id,
                sku=p.sku,
                upc=p.upc,
                product_name=p.product_name,
                brand=p.brand,
                category=p.category,
                size=p.size,
                vendor_id=p.default_vendor_id,
                vendor_name=vendor.name if vendor else None,
                units_per_case=p.units_per_case,
                snapshot_at=snap.snapshot_at if snap else None,
                current_quantity=hand,
                incoming_units=incoming_units,
                inventory_position=hand + incoming_units,
                unit_cost=cost,
                retail_price=price,
                inventory_value=inventory_value,
                margin=(price - cost) / price if price > 0 and cost is not None else None,
                sales_30=sum(units[-30:]),
                sales_90=qty90,
                revenue_90=revenue,
                gross_profit=gross_profit,
                average_daily_demand=demand.average,
                demand_std=demand.std,
                lead_time_days=lead,
                safety_stock=demand.safety,
                reorder_point=demand.reorder_point,
                target_stock=demand.target,
                days_of_supply=demand.days,
                turnover=qty90 * cost / average_value
                if average_value and cost is not None
                else None,
                gmroi=gross_profit / average_value
                if average_value and gross_profit is not None
                else None,
                inventory_average_estimated=True,
                sell_through=qty90 / (qty90 + hand) if qty90 + hand else 0,
                dead=dead,
                slow=slow,
                stockout=risk,
                abnormal_demand=abnormal,
                status=status,
                recommended_units=cases * p.units_per_case,
                recommended_cases=cases,
                estimated_cost=cases * p.units_per_case * cost if cost is not None else None,
                explanation=explanation,
                blockers=blockers,
                sales_history=[
                    {
                        "date": (start + timedelta(days=i)).isoformat(),
                        "units": x[0],
                        "revenue": round(x[1], 2),
                    }
                    for i, x in enumerate(daily)
                ][-90:],
            )
        )
    classes = abc_classes({m.product_id: m.revenue_90 for m in result})
    for m in result:
        m.abc = classes[m.product_id]
    return result


def alerts_for(metrics: list[Metrics]) -> list[Alert]:
    alerts = []
    for m in metrics:
        signals = []
        if m.stockout:
            signals.append(
                (
                    "critical",
                    "Stockout risk",
                    f"{m.days_of_supply:.1f} days of stock remaining",
                    "Review this week's Smart Order",
                )
            )
        if m.dead:
            signals.append(
                (
                    "warning",
                    "Dead inventory",
                    "No sales during the dead-stock window",
                    "Pause purchasing and review markdowns",
                )
            )
        elif m.slow:
            signals.append(
                (
                    "warning",
                    "Slow inventory",
                    "Stock exceeds the slow-stock threshold",
                    "Pause purchasing",
                )
            )
        if m.abnormal_demand:
            signals.append(
                (
                    "info",
                    "Unusual demand",
                    "Last week's daily demand is at least twice the preceding 28 days",
                    "Check promotions before changing purchases",
                )
            )
        for blocker in m.blockers:
            signals.append(
                (
                    "warning",
                    blocker.capitalize(),
                    "Recommendation held until data is resolved",
                    "Update product details or import fresh data",
                )
            )
        for severity, title, description, action in signals:
            alerts.append(
                Alert(
                    severity=severity,
                    title=title,
                    description=description,
                    product_id=m.product_id,
                    product_name=m.product_name,
                    financial_impact=m.inventory_value,
                    recommended_action=action,
                )
            )
    return sorted(
        alerts, key=lambda a: ({"critical": 0, "warning": 1, "info": 2}[a.severity], a.product_name)
    )


def persist_recommendations(db: Session, store: Store, metrics: list[Metrics]) -> None:
    for m in metrics:
        db.add(
            ReorderRecommendation(
                organization_id=store.organization_id,
                store_id=store.id,
                **m.model_dump(
                    include={
                        "product_id",
                        "vendor_id",
                        "current_quantity",
                        "average_daily_demand",
                        "lead_time_days",
                        "safety_stock",
                        "reorder_point",
                        "target_stock",
                        "recommended_units",
                        "recommended_cases",
                        "estimated_cost",
                        "status",
                        "explanation",
                    }
                ),
            )
        )
    db.commit()
