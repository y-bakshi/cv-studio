"""Request models shared by the API routers."""

from pydantic import BaseModel, EmailStr, Field


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
