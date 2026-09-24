from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from bottleiq.auth import Actor, current_actor, editor, get_store
from bottleiq.db import get_db
from bottleiq.models import IncomingStock, Product
from bottleiq.schemas import IncomingInput, IncomingUpdate, IncomingView

router = APIRouter(prefix="/incoming-stock", tags=["Incoming stock"])


def view(shipment: IncomingStock) -> dict:
    return {
        "id": shipment.id,
        "store_id": shipment.store_id,
        "product_id": shipment.product_id,
        "quantity_units": shipment.quantity_units,
        "expected_at": shipment.expected_at,
        "reference": shipment.reference,
        "status": shipment.status,
    }


@router.get("", response_model=list[IncomingView])
def list_incoming(
    store_id: str,
    product_id: str | None = None,
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
) -> list[dict]:
    get_store(db, actor, store_id)
    query = select(IncomingStock).where(
        IncomingStock.organization_id == actor.organization_id,
        IncomingStock.store_id == store_id,
        IncomingStock.status == "open",
    )
    if product_id:
        query = query.where(IncomingStock.product_id == product_id)
    return [view(item) for item in db.scalars(query.order_by(IncomingStock.expected_at))]


@router.post("", status_code=201, response_model=IncomingView)
def create(
    data: IncomingInput,
    actor: Actor = Depends(editor),
    db: Session = Depends(get_db),
) -> dict:
    store = get_store(db, actor, data.store_id)
    product = db.scalar(
        select(Product).where(
            Product.id == data.product_id,
            Product.organization_id == actor.organization_id,
            Product.active.is_(True),
        )
    )
    if product is None:
        raise HTTPException(404, "Product not found")
    if data.expected_at < datetime.now(ZoneInfo(store.timezone)).date():
        raise HTTPException(422, "Expected delivery date cannot be in the past")
    shipment = IncomingStock(
        organization_id=actor.organization_id,
        store_id=store.id,
        product_id=product.id,
        quantity_units=data.quantity_units,
        expected_at=data.expected_at,
        reference=data.reference.strip() if data.reference else None,
    )
    db.add(shipment)
    db.commit()
    return view(shipment)


@router.patch("/{shipment_id}", response_model=IncomingView)
def resolve(
    shipment_id: str,
    data: IncomingUpdate,
    actor: Actor = Depends(editor),
    db: Session = Depends(get_db),
) -> dict:
    shipment = db.scalar(
        select(IncomingStock).where(
            IncomingStock.id == shipment_id,
            IncomingStock.organization_id == actor.organization_id,
        )
    )
    if shipment is None:
        raise HTTPException(404, "Incoming stock not found")
    if shipment.status != "open":
        raise HTTPException(409, "Incoming stock is already resolved")
    shipment.status = data.status
    db.commit()
    return view(shipment)
