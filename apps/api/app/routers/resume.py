import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..dependencies import get_owned_cv
from ..models import CVDocument, User
from ..resume import Resume
from ..resume_export import resume_to_docx
from ..resume_latex import DialectError, extract_preamble, resume_to_tex, tex_to_resume
from ..services.resume_store import load_resume, write_sections

router = APIRouter(prefix="/cvs/{cv_id}/resume", tags=["Resume"])


class ResumeReplace(BaseModel):
    resume: dict
    expected_version: int


class TexReplace(BaseModel):
    tex_source: str
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
    resume = write_sections(db, cv, resume.to_sections())
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
    resume = write_sections(db, cv, {name: data})
    db.commit()
    return _payload(cv, resume)


def _tex_payload(cv: CVDocument, resume: Resume) -> dict:
    return {
        "id": cv.id,
        "version": cv.version,
        "tex_source": cv.tex_source,
        "preamble": extract_preamble(cv.tex_source),
    }


@router.get("/tex")
async def get_tex(
    cv_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cv = get_owned_cv(db, cv_id, user)
    resume = load_resume(db, cv)
    if extract_preamble(cv.tex_source) is None:
        # Legacy CV whose source predates the structured dialect.
        cv.tex_source = resume_to_tex(resume)
    return _tex_payload(cv, resume)


@router.put("/tex")
async def replace_tex(
    cv_id: str,
    body: TexReplace,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Edit the LaTeX directly; accepted only while it stays in the dialect."""
    cv = get_owned_cv(db, cv_id, user)
    _check_version(cv, body.expected_version)
    try:
        parsed = tex_to_resume(body.tex_source)
    except DialectError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(error), "line": error.line},
        )
    sections = parsed.resume.to_sections()
    sections.pop("style")  # presentation lives outside the LaTeX content dialect
    resume = write_sections(db, cv, sections, parsed.preamble)
    db.commit()
    return _tex_payload(cv, resume)


def _filename(cv: CVDocument, extension: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", cv.title).strip("_") or "resume"
    return f"{stem}.{extension}"


@router.get("/export/{fmt}")
async def export_resume(
    cv_id: str,
    fmt: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Download the résumé as ``json``, ``tex`` or ``docx`` (PDF: see /compile)."""
    cv = get_owned_cv(db, cv_id, user)
    resume = load_resume(db, cv)
    if fmt == "json":
        body, media = resume.to_json().encode(), "application/json"
    elif fmt == "tex":
        body, media = resume_to_tex(resume, extract_preamble(cv.tex_source)).encode(), "application/x-tex"
    elif fmt == "docx":
        body = resume_to_docx(resume)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown export format")
    return Response(
        body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{_filename(cv, fmt)}"'},
    )
