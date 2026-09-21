from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..dependencies import get_owned_cv
from ..models import JobDescription, User
from ..schemas import JobPaste
from ..services.job_import import MAX_UPLOAD_BYTES, extract_job_text

router = APIRouter(tags=["job descriptions"])


@router.get("/cvs/{cv_id}/job-descriptions")
async def list_jobs(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_owned_cv(db, cv_id, user)
    return db.scalars(
        select(JobDescription)
        .where(JobDescription.cv_id == cv_id, JobDescription.user_id == user.id)
        .order_by(JobDescription.created_at.desc())
    ).all()


@router.post("/cvs/{cv_id}/job-descriptions", status_code=201)
async def paste_job(
    cv_id: str,
    payload: JobPaste,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_owned_cv(db, cv_id, user)
    item = JobDescription(
        cv_id=cv_id,
        user_id=user.id,
        title=payload.title,
        content=payload.content,
        source_type="paste",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/cvs/{cv_id}/job-descriptions/upload", status_code=201)
async def upload_job(
    cv_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_owned_cv(db, cv_id, user)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "File must be under 2 MB",
        )

    filename = file.filename or "Job description"
    item = JobDescription(
        cv_id=cv_id,
        user_id=user.id,
        title=Path(filename).stem,
        content=extract_job_text(filename, data),
        source_type="upload",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
