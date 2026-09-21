from __future__ import annotations

import io
import json
import re
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from pypdf import PdfReader
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .auth import clear_session, create_session, current_user, hash_password, verify_password
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .latex import compile_tex, document_to_tex, initial_document
from .models import Annotation, CVDocument, CVRevision, Compilation, JobDescription, User, utcnow


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield
    executor.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title="CV Studio API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="latex")


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class CVCreate(BaseModel):
    title: str = Field(default="Untitled CV", min_length=1, max_length=180)
    folder: str = Field(default="My CVs", max_length=100)


class CVUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    folder: str | None = Field(default=None, max_length=100)
    document: dict | None = None
    tex_source: str | None = Field(default=None, max_length=500_000)
    expected_version: int
    starred: bool | None = None


class AnnotationCreate(BaseModel):
    block_id: str | None = None
    quoted_text: str = Field(min_length=1, max_length=10_000)
    start_offset: int | None = None
    end_offset: int | None = None
    note: str = Field(default="", max_length=20_000)


class AnnotationUpdate(BaseModel):
    note: str | None = Field(default=None, max_length=20_000)
    resolved: bool | None = None


class JobPaste(BaseModel):
    title: str = Field(default="Job description", max_length=180)
    content: str = Field(min_length=1, max_length=1_000_000)


def owned_cv(db: Session, cv_id: str, user: User) -> CVDocument:
    cv = db.scalar(select(CVDocument).where(CVDocument.id == cv_id, CVDocument.user_id == user.id))
    if not cv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CV not found")
    return cv


def cv_payload(cv: CVDocument, latest_compilation: Compilation | None = None) -> dict:
    return {
        "id": cv.id, "title": cv.title, "folder": cv.folder, "version": cv.version,
        "starred": cv.starred, "document": json.loads(cv.document_json),
        "tex_source": cv.tex_source, "updated_at": cv.updated_at,
        "latest_compilation": compilation_payload(latest_compilation) if latest_compilation else None,
    }


def compilation_payload(item: Compilation | None) -> dict | None:
    if not item: return None
    return {"id": item.id, "cv_id": item.cv_id, "status": item.status, "log": item.log, "created_at": item.created_at, "finished_at": item.finished_at, "download_url": f"/api/compilations/{item.id}/download" if item.status == "success" else None}


def create_revision(db: Session, cv: CVDocument) -> CVRevision:
    revision = CVRevision(cv_id=cv.id, user_id=cv.user_id, version=cv.version, document_json=cv.document_json, tex_source=cv.tex_source)
    db.add(revision)
    return revision


@app.get("/api/health")
async def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"ok": True, "database": "ok", "pdflatex": bool(__import__("shutil").which("pdflatex"))}


@app.post("/api/auth/register", status_code=201)
async def register(credentials: Credentials, response: Response, db: Session = Depends(get_db)):
    email = credentials.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account already exists")
    user = User(email=email, password_hash=hash_password(credentials.password))
    db.add(user); db.commit(); db.refresh(user); create_session(db, user, response)
    return {"id": user.id, "email": user.email}


@app.post("/api/auth/login")
async def login(credentials: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == credentials.email.lower().strip()))
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    create_session(db, user, response)
    return {"id": user.id, "email": user.email}


@app.post("/api/auth/logout", status_code=204)
async def logout(response: Response, request: Request, db: Session = Depends(get_db)):
    clear_session(db, response, request.cookies.get(settings.session_cookie))


@app.get("/api/auth/me")
async def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}


@app.get("/api/cvs")
async def list_cvs(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.scalars(select(CVDocument).where(CVDocument.user_id == user.id).order_by(CVDocument.updated_at.desc())).all()
    return [{"id": cv.id, "title": cv.title, "folder": cv.folder, "version": cv.version, "starred": cv.starred, "updated_at": cv.updated_at} for cv in items]


@app.post("/api/cvs", status_code=201)
async def create_cv(payload: CVCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    document = initial_document()
    cv = CVDocument(user_id=user.id, title=payload.title, folder=payload.folder, document_json=json.dumps(document), tex_source=document_to_tex(document))
    db.add(cv); db.flush(); create_revision(db, cv); db.commit(); db.refresh(cv)
    return cv_payload(cv)


@app.get("/api/cvs/{cv_id}")
async def get_cv(cv_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = owned_cv(db, cv_id, user)
    latest = db.scalar(select(Compilation).where(Compilation.cv_id == cv.id, Compilation.user_id == user.id).order_by(Compilation.created_at.desc()))
    return cv_payload(cv, latest)


@app.patch("/api/cvs/{cv_id}")
async def update_cv(cv_id: str, payload: CVUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = owned_cv(db, cv_id, user)
    if payload.expected_version != cv.version:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"message": "This CV changed in another session", "current_version": cv.version})
    if payload.title is not None: cv.title = payload.title
    if payload.folder is not None: cv.folder = payload.folder
    if payload.starred is not None: cv.starred = payload.starred
    if payload.document is not None:
        cv.document_json = json.dumps(payload.document)
        cv.tex_source = document_to_tex(payload.document)
    if payload.tex_source is not None: cv.tex_source = payload.tex_source
    cv.version += 1; cv.updated_at = utcnow(); create_revision(db, cv); db.commit(); db.refresh(cv)
    return cv_payload(cv)


@app.delete("/api/cvs/{cv_id}", status_code=204)
async def delete_cv(cv_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = owned_cv(db, cv_id, user); db.delete(cv); db.commit()


@app.get("/api/cvs/{cv_id}/revisions")
async def revisions(cv_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_cv(db, cv_id, user)
    items = db.scalars(select(CVRevision).where(CVRevision.cv_id == cv_id, CVRevision.user_id == user.id).order_by(CVRevision.version.desc())).all()
    return [{"id": item.id, "version": item.version, "created_at": item.created_at} for item in items]


@app.post("/api/cvs/{cv_id}/revisions/{revision_id}/restore")
async def restore_revision(cv_id: str, revision_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = owned_cv(db, cv_id, user)
    revision = db.scalar(select(CVRevision).where(CVRevision.id == revision_id, CVRevision.cv_id == cv.id, CVRevision.user_id == user.id))
    if not revision: raise HTTPException(status.HTTP_404_NOT_FOUND, "Revision not found")
    cv.document_json = revision.document_json; cv.tex_source = revision.tex_source; cv.version += 1; cv.updated_at = utcnow(); create_revision(db, cv); db.commit(); db.refresh(cv)
    return cv_payload(cv)


def run_compilation(compilation_id: str) -> None:
    with SessionLocal() as db:
        item = db.get(Compilation, compilation_id)
        if not item: return
        revision = db.get(CVRevision, item.revision_id)
        item.status = "compiling"; db.commit()
        output = settings.artifact_root / item.user_id / item.cv_id / f"{item.id}.pdf"
        success, log = compile_tex(revision.tex_source, output)
        item.status = "success" if success else "failed"; item.log = log[-50000:]; item.finished_at = utcnow(); item.artifact_path = str(output) if success else None; db.commit()


@app.post("/api/cvs/{cv_id}/compile", status_code=202)
async def queue_compile(cv_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cv = owned_cv(db, cv_id, user)
    revision = db.scalar(select(CVRevision).where(CVRevision.cv_id == cv.id, CVRevision.version == cv.version))
    item = Compilation(cv_id=cv.id, user_id=user.id, revision_id=revision.id)
    db.add(item); db.commit(); db.refresh(item); executor.submit(run_compilation, item.id)
    return compilation_payload(item)


@app.get("/api/compilations/{compilation_id}")
async def get_compilation(compilation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.scalar(select(Compilation).where(Compilation.id == compilation_id, Compilation.user_id == user.id))
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND, "Compilation not found")
    return compilation_payload(item)


@app.get("/api/compilations/{compilation_id}/download")
async def download_compilation(compilation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.scalar(select(Compilation).where(Compilation.id == compilation_id, Compilation.user_id == user.id, Compilation.status == "success"))
    if not item or not item.artifact_path or not Path(item.artifact_path).is_file(): raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF not available")
    title = db.get(CVDocument, item.cv_id).title
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "resume"
    return FileResponse(item.artifact_path, media_type="application/pdf", filename=f"{safe}.pdf")


@app.get("/api/cvs/{cv_id}/annotations")
async def list_annotations(cv_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_cv(db, cv_id, user)
    return db.scalars(select(Annotation).where(Annotation.cv_id == cv_id, Annotation.user_id == user.id).order_by(Annotation.created_at.desc())).all()


@app.post("/api/cvs/{cv_id}/annotations", status_code=201)
async def create_annotation(cv_id: str, payload: AnnotationCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_cv(db, cv_id, user)
    item = Annotation(cv_id=cv_id, user_id=user.id, **payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


@app.patch("/api/annotations/{annotation_id}")
async def update_annotation(annotation_id: str, payload: AnnotationUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.scalar(select(Annotation).where(Annotation.id == annotation_id, Annotation.user_id == user.id))
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND, "Annotation not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item


@app.delete("/api/annotations/{annotation_id}", status_code=204)
async def delete_annotation(annotation_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.scalar(select(Annotation).where(Annotation.id == annotation_id, Annotation.user_id == user.id))
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND, "Annotation not found")
    db.delete(item); db.commit()


@app.get("/api/cvs/{cv_id}/job-descriptions")
async def list_jobs(cv_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_cv(db, cv_id, user)
    return db.scalars(select(JobDescription).where(JobDescription.cv_id == cv_id, JobDescription.user_id == user.id).order_by(JobDescription.created_at.desc())).all()


@app.post("/api/cvs/{cv_id}/job-descriptions", status_code=201)
async def paste_job(cv_id: str, payload: JobPaste, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_cv(db, cv_id, user)
    item = JobDescription(cv_id=cv_id, user_id=user.id, title=payload.title, content=payload.content, source_type="paste"); db.add(item); db.commit(); db.refresh(item); return item


@app.post("/api/cvs/{cv_id}/job-descriptions/upload", status_code=201)
async def upload_job(cv_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_cv(db, cv_id, user); data = await file.read(2_000_001)
    if len(data) > 2_000_000: raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File must be under 2 MB")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in {".txt", ".md"}: content = data.decode("utf-8", errors="replace")
    elif suffix == ".pdf": content = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    else: raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Use TXT, Markdown, or text-based PDF")
    if not content.strip(): raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No text could be extracted")
    item = JobDescription(cv_id=cv_id, user_id=user.id, title=Path(file.filename or "Job description").stem, content=content[:1_000_000], source_type="upload"); db.add(item); db.commit(); db.refresh(item); return item
