from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..dependencies import get_owned_cv
from ..models import Annotation, User
from ..schemas import AnnotationCreate, AnnotationUpdate

router = APIRouter(tags=["annotations"])


@router.get("/cvs/{cv_id}/annotations")
async def list_annotations(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_owned_cv(db, cv_id, user)
    return db.scalars(
        select(Annotation)
        .where(Annotation.cv_id == cv_id, Annotation.user_id == user.id)
        .order_by(Annotation.created_at.desc())
    ).all()


@router.post("/cvs/{cv_id}/annotations", status_code=201)
async def create_annotation(
    cv_id: str,
    payload: AnnotationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_owned_cv(db, cv_id, user)
    item = Annotation(cv_id=cv_id, user_id=user.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/annotations/{annotation_id}")
async def update_annotation(
    annotation_id: str,
    payload: AnnotationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    item = db.scalar(
        select(Annotation).where(
            Annotation.id == annotation_id,
            Annotation.user_id == user.id,
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Annotation not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/annotations/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    item = db.scalar(
        select(Annotation).where(
            Annotation.id == annotation_id,
            Annotation.user_id == user.id,
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Annotation not found")
    db.delete(item)
    db.commit()
