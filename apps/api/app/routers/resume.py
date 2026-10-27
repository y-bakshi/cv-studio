from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..dependencies import get_owned_cv
from ..models import CVDocument, User
from ..resume import Resume
from ..services.resume_store import load_resume, write_sections

router = APIRouter(prefix="/cvs/{cv_id}/resume", tags=["Resume"])


class ResumeReplace(BaseModel):
    resume: dict
    expected_version: int


class SectionReplace(BaseModel):
    data: object
    expected_version: int


def _payload(cv: CVDocument, resume: Resume) -> dict:
    # The whole résumé as one JSON document, exactly what the user can copy.
    return {"id": cv.id, "version": cv.version, "resume": resume.to_sections()}


def _check_version(cv: CVDocument, expected: int) -> None:
    if expected != cv.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "message": "This CV changed in another session",
                "current_version": cv.version,
            },
        )


@router.get("")
async def get_resume(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cv = get_owned_cv(db, cv_id, user)
    return _payload(cv, load_resume(db, cv))


@router.put("")
async def replace_resume(
    cv_id: str,
    body: ResumeReplace,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cv = get_owned_cv(db, cv_id, user)
    _check_version(cv, body.expected_version)
    try:
        resume = Resume.model_validate(body.resume)
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, error.errors(include_url=False, include_context=False))
    write_sections(db, cv, resume.to_sections())
    db.commit()
    return _payload(cv, resume)


@router.put("/sections/{name}")
async def replace_section(
    cv_id: str,
    name: str,
    body: SectionReplace,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if name not in Resume.SECTIONS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown section")
    cv = get_owned_cv(db, cv_id, user)
    _check_version(cv, body.expected_version)
    try:
        data = Resume.validate_section(name, body.data)
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, error.errors(include_url=False, include_context=False))
    write_sections(db, cv, {name: data})
    db.commit()
    return _payload(cv, load_resume(db, cv))
