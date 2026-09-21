from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uuid_string() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CVDocument(Base):
    __tablename__ = "cv_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180), default="Untitled CV")
    folder: Mapped[str] = mapped_column(String(100), default="My CVs")
    document_json: Mapped[str] = mapped_column(Text)
    tex_source: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    starred: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CVRevision(Base):
    __tablename__ = "cv_revisions"
    __table_args__ = (UniqueConstraint("cv_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    cv_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    document_json: Mapped[str] = mapped_column(Text)
    tex_source: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Annotation(Base):
    __tablename__ = "annotations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    cv_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    block_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quoted_text: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class JobDescription(Base):
    __tablename__ = "job_descriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    cv_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    source_type: Mapped[str] = mapped_column(String(20), default="paste")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Compilation(Base):
    __tablename__ = "compilations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    cv_id: Mapped[str] = mapped_column(ForeignKey("cv_documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("cv_revisions.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    log: Mapped[str] = mapped_column(Text, default="")
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

