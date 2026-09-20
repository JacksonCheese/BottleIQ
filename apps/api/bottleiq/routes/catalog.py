from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bottleiq.auth import Actor, current_actor, editor, get_store
from bottleiq.db import get_db
from bottleiq.models import Product, Store, Vendor
from bottleiq.schemas import (
    Alert,
    AnalysisOptions,
    GenerateInput,
    Metrics,
    ProductEdit,
    StoreInput,
    VendorInput,
)
from bottleiq.services.analytics import alerts_for, analyze, persist_recommendations

router = APIRouter(tags=["Inventory intelligence"])


@router.get("/stores")
def stores(actor: Actor = Depends(current_actor), db: Session = Depends(get_db)) -> list[dict]:
    return [
        {"id": s.id, "name": s.name, "timezone": s.timezone}
        for s in db.scalars(
            select(Store)
            .where(Store.organization_id == actor.organization_id)
            .order_by(Store.created_at)
        )
    ]


@router.post("/stores", status_code=201)
def create_store(
    data: StoreInput, actor: Actor = Depends(editor), db: Session = Depends(get_db)
) -> dict:
    store = Store(organization_id=actor.organization_id, **data.model_dump())
    db.add(store)
    db.commit()
    return {"id": store.id, "name": store.name, "timezone": store.timezone}


@router.get("/vendors")
def vendors(actor: Actor = Depends(current_actor), db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "id": v.id,
            "name": v.name,
            "default_lead_time_days": v.default_lead_time_days,
            "minimum_order_amount": float(v.minimum_order_amount)
            if v.minimum_order_amount is not None
            else None,
        }
        for v in db.scalars(
            select(Vendor)
            .where(Vendor.organization_id == actor.organization_id)
            .order_by(Vendor.name)
        )
    ]


@router.post("/vendors", status_code=201)
def create_vendor(
    data: VendorInput, actor: Actor = Depends(editor), db: Session = Depends(get_db)
) -> dict:
    vendor = Vendor(organization_id=actor.organization_id, **data.model_dump())
    db.add(vendor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A distributor with this name already exists") from exc
    return {"id": vendor.id, "name": vendor.name}


@router.patch("/vendors/{vendor_id}")
def update_vendor(
    vendor_id: str, data: VendorInput, actor: Actor = Depends(editor), db: Session = Depends(get_db)
) -> dict:
    vendor = db.scalar(
        select(Vendor).where(
            Vendor.id == vendor_id, Vendor.organization_id == actor.organization_id
        )
    )
    if not vendor:
        raise HTTPException(404, "Distributor not found")
    for key, value in data.model_dump().items():
        setattr(vendor, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A distributor with this name already exists") from exc
    return {"id": vendor.id, "name": vendor.name}


@router.get("/inventory", response_model=list[Metrics])
@router.get("/products", response_model=list[Metrics])
@router.get("/recommendations", response_model=list[Metrics])
def inventory(
    store_id: str,
    options: AnalysisOptions = Depends(),
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
) -> list[Metrics]:
    return analyze(db, get_store(db, actor, store_id), options)


@router.get("/products/{product_id}", response_model=Metrics)
def product_detail(
    product_id: str,
    store_id: str,
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
) -> Metrics:
    found = next(
        (m for m in analyze(db, get_store(db, actor, store_id)) if m.product_id == product_id), None
    )
    if not found:
        raise HTTPException(404, "Product not found in this store")
    return found


@router.patch("/products/{product_id}")
def update_product(
    product_id: str,
    data: ProductEdit,
    actor: Actor = Depends(editor),
    db: Session = Depends(get_db),
) -> dict:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id, Product.organization_id == actor.organization_id
        )
    )
    if not product:
        raise HTTPException(404, "Product not found")
    if data.default_vendor_id and not db.scalar(
        select(Vendor).where(
            Vendor.id == data.default_vendor_id, Vendor.organization_id == actor.organization_id
        )
    ):
        raise HTTPException(422, "Select a distributor from your organization")
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.commit()
    return {"id": product.id}


@router.get("/alerts", response_model=list[Alert])
def alerts(
    store_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> list[Alert]:
    return alerts_for(analyze(db, get_store(db, actor, store_id)))


@router.post("/recommendations/generate", response_model=list[Metrics])
def generate(
    data: GenerateInput, actor: Actor = Depends(editor), db: Session = Depends(get_db)
) -> list[Metrics]:
    store = get_store(db, actor, data.store_id)
    metrics = analyze(db, store, data)
    persist_recommendations(db, store, metrics)
    return metrics


@router.get("/dashboard")
def dashboard(
    store_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> dict:
    metrics = analyze(db, get_store(db, actor, store_id))
    categories: dict[str, float] = {}
    statuses: dict[str, int] = {}
    for m in metrics:
        categories[m.category] = categories.get(m.category, 0) + (m.inventory_value or 0)
        statuses[m.status] = statuses.get(m.status, 0) + 1
    return {
        "inventory_value": sum(m.inventory_value or 0 for m in metrics),
        "slow_value": sum(m.inventory_value or 0 for m in metrics if m.slow and not m.dead),
        "dead_value": sum(m.inventory_value or 0 for m in metrics if m.dead),
        "stockout_risks": sum(m.stockout for m in metrics),
        "recommended_reorders": sum(m.recommended_cases > 0 for m in metrics),
        "order_cost": sum(m.estimated_cost or 0 for m in metrics),
        "missing_cost_count": sum(m.unit_cost is None for m in metrics),
        "categories": [
            {"name": name, "value": round(value, 2)} for name, value in categories.items()
        ],
        "statuses": statuses,
        "attention": [a.model_dump() for a in alerts_for(metrics)[:8]],
        "top_profit": [
            m.model_dump()
            for m in sorted(metrics, key=lambda m: m.gross_profit or 0, reverse=True)[:5]
        ],
        "cash_tied_up": [
            m.model_dump()
            for m in sorted(
                [m for m in metrics if m.slow], key=lambda m: m.inventory_value or 0, reverse=True
            )[:5]
        ],
        "actions": [
            m.model_dump()
            for m in sorted(
                [m for m in metrics if m.recommended_cases], key=lambda m: m.days_of_supply or 0
            )[:5]
        ],
        "product_count": len(metrics),
        "latest_snapshot": max((m.snapshot_at for m in metrics if m.snapshot_at), default=None),
    }
