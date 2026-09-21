import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from bottleiq.auth import Actor, current_actor, editor, get_store
from bottleiq.config import settings
from bottleiq.db import get_db
from bottleiq.models import ImportJob
from bottleiq.schemas import ImportJobView
from bottleiq.services.imports import FIELDS, import_csv

router = APIRouter(prefix="/imports", tags=["Imports"])


@router.get("/fields")
def fields() -> dict:
    return FIELDS


@router.get("", response_model=list[ImportJobView])
def jobs(
    store_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> list[dict]:
    get_store(db, actor, store_id)
    return [
        job_dict(j)
        for j in db.scalars(
            select(ImportJob)
            .where(
                ImportJob.store_id == store_id, ImportJob.organization_id == actor.organization_id
            )
            .order_by(ImportJob.created_at.desc())
            .limit(100)
        )
    ]


def job_dict(job: ImportJob) -> dict:
    return {
        field: getattr(job, field)
        for field in (
            "id",
            "filename",
            "import_type",
            "status",
            "row_count",
            "rows_imported",
            "rows_rejected",
            "rows_duplicate",
            "error_summary",
            "created_at",
        )
    }


@router.get("/{job_id}/errors", response_class=PlainTextResponse)
def rejected_rows(
    job_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> str:
    job = db.scalar(
        select(ImportJob).where(
            ImportJob.id == job_id, ImportJob.organization_id == actor.organization_id
        )
    )
    if not job:
        raise HTTPException(404, "Import not found")
    return (
        "\n".join(f"Row {e['row']}: {e['message']}" for e in job.error_summary)
        or "No rejected rows"
    )


@router.post("/{kind}", response_model=ImportJobView)
async def upload(
    kind: Literal["sales", "inventory", "purchases"],
    store_id: str = Form(...),
    mapping: str = Form("{}"),
    file: UploadFile = File(...),
    actor: Actor = Depends(editor),
    db: Session = Depends(get_db),
) -> dict:
    store = get_store(db, actor, store_id)
    try:
        content = await file.read(settings().max_upload_bytes + 1)
    finally:
        await file.close()
    if len(content) > settings().max_upload_bytes:
        raise HTTPException(413, "CSV exceeds the 10 MB limit")
    try:
        column_map = json.loads(mapping)
        if not isinstance(column_map, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in column_map.items()
        ):
            raise ValueError("Column mapping must map field names to CSV headers")
        job = await run_in_threadpool(
            import_csv, db, store, kind, content, file.filename or "upload.csv", column_map
        )
        return job_dict(job)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409, "This file is being imported concurrently. Refresh import history."
        ) from exc
