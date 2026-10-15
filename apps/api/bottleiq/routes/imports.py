import json
from datetime import UTC, date, datetime
from decimal import Decimal
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
from bottleiq.schemas import ImportJobView, ImportResolution
from bottleiq.services.analytics import analyze
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


@router.get("/quality")
def quality_report(
    store_id: str, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> dict:
    store = get_store(db, actor, store_id)
    metrics = analyze(db, store)
    reasons: dict[str, int] = {}
    for metric in metrics:
        for blocker in metric.blockers:
            reasons[blocker] = reasons.get(blocker, 0) + 1
    return {
        "store_id": store.id,
        "products_checked": len(metrics),
        "products_held": sum(bool(metric.blockers) for metric in metrics),
        "reasons": reasons,
    }


def job_dict(job: ImportJob) -> dict:
    # Warnings share the stored summary column; imported rows with notes are not rejections.
    entries = job.error_summary or []
    return {
        **{
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
                "coverage_start",
                "coverage_end",
                "reconciliation",
                "resolved_at",
                "resolved_by_user_id",
                "resolution_note",
                "created_at",
            )
        },
        "error_summary": [e for e in entries if e.get("level") != "warning"],
        "warnings": [e for e in entries if e.get("level") == "warning"],
    }


@router.post("/{job_id}/resolve", response_model=ImportJobView)
def resolve_import(
    job_id: str,
    data: ImportResolution,
    actor: Actor = Depends(current_actor),
    db: Session = Depends(get_db),
) -> dict:
    if actor.role != "owner":
        raise HTTPException(403, "Only an owner can resolve an import issue")
    job = db.scalar(
        select(ImportJob)
        .where(ImportJob.id == job_id, ImportJob.organization_id == actor.organization_id)
        .with_for_update()
    )
    if not job:
        raise HTTPException(404, "Import not found")
    if job.resolved_at:
        raise HTTPException(409, "This import issue has already been resolved")
    if (
        not job.rows_rejected
        and not any(entry.get("level") == "warning" for entry in (job.error_summary or []))
        and (job.reconciliation or {}).get("status") not in ("mismatch", "rejected")
    ):
        raise HTTPException(422, "This import has no recorded issue to resolve")
    later = db.scalars(
        select(ImportJob).where(
            ImportJob.store_id == job.store_id,
            ImportJob.organization_id == actor.organization_id,
            ImportJob.import_type == job.import_type,
            ImportJob.created_at > job.created_at,
            ImportJob.status == "completed",
        )
    ).all()
    if not any(
        candidate.import_type != "sales"
        or (candidate.reconciliation or {}).get("status") == "matched"
        for candidate in later
    ):
        raise HTTPException(409, "Import a corrected, complete export before recording resolution")
    job.resolved_at = datetime.now(UTC)
    job.resolved_by_user_id = actor.user.id
    job.resolution_note = data.note
    db.commit()
    return job_dict(job)


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
        "\n".join(
            f"Row {e['row']}{' (imported with a note)' if e.get('level') == 'warning' else ''}: "
            f"{e['message']}"
            for e in job.error_summary
        )
        or "No rejected rows"
    )


@router.post("/{kind}", response_model=ImportJobView)
async def upload(
    kind: Literal["sales", "inventory", "purchases"],
    store_id: str = Form(...),
    mapping: str = Form("{}"),
    coverage_start: date | None = Form(None),
    coverage_end: date | None = Form(None),
    expected_rows: int | None = Form(None),
    expected_units: int | None = Form(None),
    expected_revenue: Decimal | None = Form(None),
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
            import_csv,
            db,
            store,
            kind,
            content,
            file.filename or "upload.csv",
            column_map,
            coverage_start,
            coverage_end,
            expected_rows,
            expected_units,
            expected_revenue,
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
