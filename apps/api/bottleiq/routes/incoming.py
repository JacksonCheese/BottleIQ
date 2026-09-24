from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from bottleiq.auth import Actor, current_actor, editor, get_store
from bottleiq.db import get_db
from bottleiq.models import IncomingStock, Product, StockReceipt
from bottleiq.schemas import IncomingInput, IncomingUpdate, IncomingView, ReceiptInput

router = APIRouter(prefix="/incoming-stock", tags=["Incoming stock"])


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def view(db: Session, shipment: IncomingStock) -> dict:
    receipts = db.scalars(
        select(StockReceipt).where(
            StockReceipt.incoming_stock_id == shipment.id,
            StockReceipt.organization_id == shipment.organization_id,
        )
    ).all()
    received = sum(receipt.quantity_units for receipt in receipts)
    return {
        "id": shipment.id,
        "store_id": shipment.store_id,
        "product_id": shipment.product_id,
        "quantity_units": shipment.quantity_units,
        "expected_at": shipment.expected_at,
        "reference": shipment.reference,
        "status": shipment.status,
        "received_units": received,
        "remaining_units": max(0, shipment.quantity_units - received),
        "last_received_at": max((utc(r.received_at) for r in receipts), default=None),
        "receipts": [
            {
                "id": receipt.id,
                "quantity_units": receipt.quantity_units,
                "received_at": utc(receipt.received_at),
                "recorded_by_user_id": receipt.recorded_by_user_id,
            }
            for receipt in sorted(
                receipts, key=lambda receipt: (utc(receipt.received_at), receipt.id)
            )
        ],
    }


@router.get("", response_model=list[IncomingView])
def list_incoming(
    store_id: str,
    product_id: str | None = None,
    include_closed: bool = False,
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
) -> list[dict]:
    get_store(db, actor, store_id)
    query = select(IncomingStock).where(
        IncomingStock.organization_id == actor.organization_id,
        IncomingStock.store_id == store_id,
    )
    if not include_closed:
        query = query.where(IncomingStock.status == "open")
    if product_id:
        query = query.where(IncomingStock.product_id == product_id)
    return [view(db, item) for item in db.scalars(query.order_by(IncomingStock.expected_at))]


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
    return view(db, shipment)


@router.post("/{shipment_id}/receive", response_model=IncomingView)
def receive(
    shipment_id: str,
    data: ReceiptInput,
    actor: Actor = Depends(editor),
    db: Session = Depends(get_db),
) -> dict:
    shipment = db.scalar(
        select(IncomingStock)
        .where(
            IncomingStock.id == shipment_id,
            IncomingStock.organization_id == actor.organization_id,
        )
        .with_for_update()
    )
    if shipment is None:
        raise HTTPException(404, "Incoming stock not found")
    if shipment.status != "open":
        raise HTTPException(409, "Incoming stock is already closed")
    received = sum(
        db.scalars(
            select(StockReceipt.quantity_units).where(
                StockReceipt.incoming_stock_id == shipment.id,
                StockReceipt.organization_id == actor.organization_id,
            )
        )
    )
    if data.quantity_units > shipment.quantity_units - received:
        raise HTTPException(422, "Received quantity exceeds units still expected")
    db.add(
        StockReceipt(
            organization_id=actor.organization_id,
            store_id=shipment.store_id,
            product_id=shipment.product_id,
            incoming_stock_id=shipment.id,
            recorded_by_user_id=actor.user.id,
            quantity_units=data.quantity_units,
        )
    )
    if received + data.quantity_units == shipment.quantity_units:
        shipment.status = "resolved"
    db.commit()
    return view(db, shipment)


@router.patch("/{shipment_id}", response_model=IncomingView)
def resolve(
    shipment_id: str,
    data: IncomingUpdate,
    actor: Actor = Depends(editor),
    db: Session = Depends(get_db),
) -> dict:
    shipment = db.scalar(
        select(IncomingStock)
        .where(
            IncomingStock.id == shipment_id,
            IncomingStock.organization_id == actor.organization_id,
        )
        .with_for_update()
    )
    if shipment is None:
        raise HTTPException(404, "Incoming stock not found")
    if shipment.status != "open":
        raise HTTPException(409, "Incoming stock is already resolved")
    shipment.status = data.status
    db.commit()
    return view(db, shipment)
