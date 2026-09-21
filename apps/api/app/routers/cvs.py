import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..dependencies import get_owned_cv
from ..latex import document_to_tex, initial_document
from ..models import CVDocument, CVRevision, Compilation, User, utcnow
from ..schemas import CVCreate, CVUpdate
from ..serializers import cv_payload
from ..services.revisions import snapshot_revision

router = APIRouter(prefix="/cvs", tags=["CVs"])


@router.get("")
async def list_cvs(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    items = db.scalars(
        select(CVDocument)
        .where(CVDocument.user_id == user.id)
        .order_by(CVDocument.updated_at.desc())
    ).all()
    return [
        {
            "id": cv.id,
            "title": cv.title,
            "folder": cv.folder,
            "version": cv.version,
            "starred": cv.starred,
            "updated_at": cv.updated_at,
        }
        for cv in items
    ]


@router.post("", status_code=201)
async def create_cv(
    payload: CVCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    document = initial_document()
    cv = CVDocument(
        user_id=user.id,
        title=payload.title,
        folder=payload.folder,
        document_json=json.dumps(document),
        tex_source=document_to_tex(document),
    )
    db.add(cv)
    db.flush()
    snapshot_revision(db, cv)
    db.commit()
    db.refresh(cv)
    return cv_payload(cv)


@router.get("/{cv_id}")
async def get_cv(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cv = get_owned_cv(db, cv_id, user)
    latest = db.scalar(
        select(Compilation)
        .where(Compilation.cv_id == cv.id, Compilation.user_id == user.id)
        .order_by(Compilation.created_at.desc())
    )
    return cv_payload(cv, latest)


@router.patch("/{cv_id}")
async def update_cv(
    cv_id: str,
    payload: CVUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cv = get_owned_cv(db, cv_id, user)
    if payload.expected_version != cv.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "message": "This CV changed in another session",
                "current_version": cv.version,
            },
        )

    if payload.title is not None:
        cv.title = payload.title
    if payload.folder is not None:
        cv.folder = payload.folder
    if payload.starred is not None:
        cv.starred = payload.starred
    if payload.document is not None:
        cv.document_json = json.dumps(payload.document)
        cv.tex_source = document_to_tex(payload.document)
    if payload.tex_source is not None:
        cv.tex_source = payload.tex_source

    cv.version += 1
    cv.updated_at = utcnow()
    snapshot_revision(db, cv)
    db.commit()
    db.refresh(cv)
    return cv_payload(cv)


@router.delete("/{cv_id}", status_code=204)
async def delete_cv(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cv = get_owned_cv(db, cv_id, user)
    db.delete(cv)
    db.commit()


@router.get("/{cv_id}/revisions")
async def list_revisions(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_owned_cv(db, cv_id, user)
    items = db.scalars(
        select(CVRevision)
        .where(CVRevision.cv_id == cv_id, CVRevision.user_id == user.id)
        .order_by(CVRevision.version.desc())
    ).all()
    return [
        {"id": item.id, "version": item.version, "created_at": item.created_at}
        for item in items
    ]


@router.post("/{cv_id}/revisions/{revision_id}/restore")
async def restore_revision(
    cv_id: str,
    revision_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cv = get_owned_cv(db, cv_id, user)
    revision = db.scalar(
        select(CVRevision).where(
            CVRevision.id == revision_id,
            CVRevision.cv_id == cv.id,
            CVRevision.user_id == user.id,
        )
    )
    if revision is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Revision not found")

    cv.document_json = revision.document_json
    cv.tex_source = revision.tex_source
    cv.version += 1
    cv.updated_at = utcnow()
    snapshot_revision(db, cv)
    db.commit()
    db.refresh(cv)
    return cv_payload(cv)
