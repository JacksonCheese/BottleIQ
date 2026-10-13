from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bottleiq.auth import Actor, current_actor, editor, get_store
from bottleiq.db import get_db
from bottleiq.schemas import ProgressStart, ProgressView
from bottleiq.services.progress import (
    TrackingExists,
    progress_report,
    start_tracking,
    stop_tracking,
)

router = APIRouter(prefix="/progress", tags=["Progress"])
ALREADY_STARTED = (
    "Tracking already started for this store. Restart tracking to choose a new start date."
)


@router.get("", response_model=ProgressView)
def progress(
    store_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> dict:
    return progress_report(db, get_store(db, actor, store_id))


@router.post("", status_code=201, response_model=ProgressView)
def start(
    data: ProgressStart, actor: Actor = Depends(editor), db: Session = Depends(get_db)
) -> dict:
    store = get_store(db, actor, data.store_id)
    try:
        start_tracking(db, store, actor.user.id, data.started_on)
    except TrackingExists as exc:
        raise HTTPException(409, ALREADY_STARTED) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, ALREADY_STARTED) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return progress_report(db, store)


@router.delete("", status_code=204)
def restart(
    store_id: str, actor: Actor = Depends(editor), db: Session = Depends(get_db)
) -> Response:
    stop_tracking(db, get_store(db, actor, store_id))
    return Response(status_code=204)
