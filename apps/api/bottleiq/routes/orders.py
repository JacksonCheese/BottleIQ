from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from bottleiq.auth import Actor, current_actor, editor, get_store
from bottleiq.db import get_db
from bottleiq.models import SmartOrder
from bottleiq.schemas import OrderEdit, OrderInput
from bottleiq.services.orders import create_order, edit_order, export_order, order_detail

router = APIRouter(prefix="/smart-orders", tags=["Smart Orders"])


def find_order(db: Session, actor: Actor, order_id: str, lock: bool = False) -> SmartOrder:
    query = select(SmartOrder).where(
        SmartOrder.id == order_id, SmartOrder.organization_id == actor.organization_id
    )
    order = db.scalar(query.with_for_update() if lock else query)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.post("", status_code=201)
def create(data: OrderInput, actor: Actor = Depends(editor), db: Session = Depends(get_db)) -> dict:
    return order_detail(db, create_order(db, get_store(db, actor, data.store_id), data))


@router.get("")
def orders(
    store_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> list[dict]:
    get_store(db, actor, store_id)
    return [
        order_detail(db, order)
        for order in db.scalars(
            select(SmartOrder)
            .where(
                SmartOrder.store_id == store_id, SmartOrder.organization_id == actor.organization_id
            )
            .order_by(SmartOrder.generated_at.desc())
            .limit(100)
        )
    ]


@router.get("/{order_id}")
def detail(
    order_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> dict:
    return order_detail(db, find_order(db, actor, order_id))


@router.patch("/{order_id}")
def update(
    order_id: str, data: OrderEdit, actor: Actor = Depends(editor), db: Session = Depends(get_db)
) -> dict:
    order = find_order(db, actor, order_id, lock=True)
    edit_order(db, order, data)
    return order_detail(db, order)


@router.get("/{order_id}/export")
def export(
    order_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> Response:
    detail = order_detail(db, find_order(db, actor, order_id))
    return Response(
        export_order(detail),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="bottleiq-order-{order_id}.csv"'},
    )
