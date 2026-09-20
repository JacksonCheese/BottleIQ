import csv
import io
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from bottleiq.models import Product, SmartOrder, SmartOrderLine, Store, Vendor
from bottleiq.schemas import OrderEdit, OrderInput
from bottleiq.services.analytics import analyze, persist_recommendations


def create_order(db: Session, store: Store, data: OrderInput) -> SmartOrder:
    vendor = db.scalar(
        select(Vendor).where(
            Vendor.id == data.vendor_id, Vendor.organization_id == store.organization_id
        )
    )
    if not vendor:
        raise HTTPException(404, "Distributor not found")
    metrics = analyze(db, store, data)
    selected = [m for m in metrics if m.vendor_id == vendor.id and m.recommended_cases > 0]
    if not selected:
        raise HTTPException(422, "No eligible items to reorder for this distributor")
    persist_recommendations(db, store, metrics)
    order = SmartOrder(
        organization_id=store.organization_id, store_id=store.id, vendor_id=vendor.id
    )
    db.add(order)
    db.flush()
    total = Decimal(0)
    for m in selected:
        unit_cost = Decimal(str(m.unit_cost)).quantize(Decimal("0.01"))
        line_total = unit_cost * m.recommended_units
        total += line_total
        db.add(
            SmartOrderLine(
                organization_id=store.organization_id,
                smart_order_id=order.id,
                product_id=m.product_id,
                recommended_units=m.recommended_units,
                recommended_cases=m.recommended_cases,
                units_per_case=m.units_per_case,
                unit_cost=unit_cost,
                line_total=line_total,
                explanation=m.explanation,
            )
        )
    order.estimated_total_cost = total
    db.commit()
    return order


def order_detail(db: Session, order: SmartOrder) -> dict:
    vendor = db.get(Vendor, order.vendor_id)
    lines = db.execute(
        select(SmartOrderLine, Product)
        .join(Product, Product.id == SmartOrderLine.product_id)
        .where(
            SmartOrderLine.smart_order_id == order.id,
            SmartOrderLine.organization_id == order.organization_id,
        )
        .order_by(Product.product_name)
    ).all()
    minimum = float(vendor.minimum_order_amount) if vendor and vendor.minimum_order_amount else None
    return {
        "id": order.id,
        "store_id": order.store_id,
        "vendor_id": order.vendor_id,
        "vendor_name": vendor.name if vendor else "Unknown",
        "generated_at": order.generated_at,
        "status": order.status,
        "version": order.version,
        "estimated_total_cost": float(order.estimated_total_cost),
        "minimum_order_amount": minimum,
        "below_minimum": minimum is not None and float(order.estimated_total_cost) < minimum,
        "lines": [
            {
                "product_id": p.id,
                "sku": p.sku,
                "product_name": p.product_name,
                "cases": line.recommended_cases,
                "units": line.recommended_units,
                "units_per_case": line.units_per_case,
                "unit_cost": float(line.unit_cost),
                "line_total": float(line.line_total),
                "explanation": line.explanation,
            }
            for line, p in lines
        ],
    }


def edit_order(db: Session, order: SmartOrder, data: OrderEdit) -> None:
    if order.version != data.version:
        raise HTTPException(409, "This order changed. Refresh before saving again.")
    edits = {line.product_id: line.cases for line in data.lines}
    if len(edits) != len(data.lines):
        raise HTTPException(422, "Duplicate product in changes")
    lines = db.scalars(
        select(SmartOrderLine).where(
            SmartOrderLine.smart_order_id == order.id,
            SmartOrderLine.organization_id == order.organization_id,
        )
    ).all()
    if set(edits) - {line.product_id for line in lines}:
        raise HTTPException(422, "An item does not belong to this order")
    total = Decimal(0)
    for line in lines:
        if line.product_id in edits:
            line.recommended_cases = edits[line.product_id]
            line.recommended_units = line.recommended_cases * line.units_per_case
            line.line_total = line.recommended_units * line.unit_cost
        total += line.line_total
    order.estimated_total_cost = total
    order.version += 1
    db.commit()


def safe_csv(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def export_order(detail: dict) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "vendor",
            "sku",
            "product_name",
            "cases",
            "units",
            "unit_cost",
            "line_total",
            "explanation",
        ]
    )
    for line in detail["lines"]:
        if line["cases"]:
            writer.writerow(
                [
                    safe_csv(value)
                    for value in [
                        detail["vendor_name"],
                        line["sku"],
                        line["product_name"],
                        line["cases"],
                        line["units"],
                        line["unit_cost"],
                        line["line_total"],
                        line["explanation"],
                    ]
                ]
            )
    return stream.getvalue()
