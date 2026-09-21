import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..dependencies import get_owned_cv
from ..models import CVDocument, CVRevision, Compilation, User
from ..serializers import compilation_payload
from ..services.compilation import submit_compilation

router = APIRouter(tags=["compilations"])


@router.post("/cvs/{cv_id}/compile", status_code=202)
async def queue_compile(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cv = get_owned_cv(db, cv_id, user)
    revision = db.scalar(
        select(CVRevision).where(
            CVRevision.cv_id == cv.id,
            CVRevision.version == cv.version,
        )
    )
    if revision is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The current CV version has no source revision",
        )

    item = Compilation(
        cv_id=cv.id,
        user_id=user.id,
        revision_id=revision.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    submit_compilation(item.id)
    return compilation_payload(item)


@router.get("/compilations/{compilation_id}")
async def get_compilation(
    compilation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    item = db.scalar(
        select(Compilation).where(
            Compilation.id == compilation_id,
            Compilation.user_id == user.id,
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compilation not found")
    return compilation_payload(item)


@router.get("/compilations/{compilation_id}/download")
async def download_compilation(
    compilation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    item = db.scalar(
        select(Compilation).where(
            Compilation.id == compilation_id,
            Compilation.user_id == user.id,
            Compilation.status == "success",
        )
    )
    if (
        item is None
        or not item.artifact_path
        or not Path(item.artifact_path).is_file()
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF not available")

    cv = db.get(CVDocument, item.cv_id)
    title = cv.title if cv is not None else "resume"
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "resume"
    return FileResponse(
        item.artifact_path,
        media_type="application/pdf",
        filename=f"{safe_title}.pdf",
    )
