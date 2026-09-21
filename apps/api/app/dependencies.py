"""Reusable authorization-aware database dependencies."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CVDocument, User


def get_owned_cv(db: Session, cv_id: str, user: User) -> CVDocument:
    """Return a CV only when it belongs to the authenticated user.

    Returning 404 for both missing and foreign records avoids disclosing whether
    another user's document exists.
    """
    cv = db.scalar(
        select(CVDocument).where(
            CVDocument.id == cv_id,
            CVDocument.user_id == user.id,
        )
    )
    if cv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CV not found")
    return cv
