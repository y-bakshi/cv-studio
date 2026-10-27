"""Structured résumé model.

A résumé is one ``Resume`` object. Each top-level field is a *section* that is
stored as its own JSON document in the database (see ``services/resume_store``)
and the whole object is served to the frontend as a single JSON document.
"""

from __future__ import annotations

import json
import uuid
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


def _id() -> str:
    return uuid.uuid4().hex[:12]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Link(_Model):
    id: str = Field(default_factory=_id)
    label: str = Field(default="", max_length=120)
    url: str = Field(default="", max_length=2048)


class Contact(_Model):
    name: str = Field(default="", max_length=180)
    subtitle: str = Field(default="", max_length=240)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=60)
    location: str = Field(default="", max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=30)
    links: list[Link] = Field(default_factory=list, max_length=20)


class SkillGroup(_Model):
    id: str = Field(default_factory=_id)
    name: str = Field(default="", max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=100)


class ExperienceEntry(_Model):
    id: str = Field(default_factory=_id)
    company: str = Field(default="", max_length=180)
    role: str = Field(default="", max_length=180)
    location: str = Field(default="", max_length=120)
    start: str = Field(default="", max_length=40)
    end: str = Field(default="", max_length=40)
    summary: str = Field(default="", max_length=2000)
    bullets: list[str] = Field(default_factory=list, max_length=30)


class ProjectEntry(_Model):
    id: str = Field(default_factory=_id)
    name: str = Field(default="", max_length=180)
    link_text: str = Field(default="", max_length=120)
    organization: str = Field(default="", max_length=180)
    location: str = Field(default="", max_length=120)
    start: str = Field(default="", max_length=40)
    end: str = Field(default="", max_length=40)
    bullets: list[str] = Field(default_factory=list, max_length=30)


class EducationEntry(_Model):
    id: str = Field(default_factory=_id)
    school: str = Field(default="", max_length=180)
    degree: str = Field(default="", max_length=180)
    location: str = Field(default="", max_length=120)
    start: str = Field(default="", max_length=40)
    end: str = Field(default="", max_length=40)
    gpa: str = Field(default="", max_length=20)
    achievements: list[str] = Field(default_factory=list, max_length=30)
    coursework: list[str] = Field(default_factory=list, max_length=50)
    bullets: list[str] = Field(default_factory=list, max_length=30)


class Resume(_Model):
    """One résumé: the unit the frontend loads, edits and lets users copy."""

    SECTION_TYPES: ClassVar[dict[str, object]] = {
        "contact": Contact,
        "skills": list[SkillGroup],
        "experience": list[ExperienceEntry],
        "projects": list[ProjectEntry],
        "education": list[EducationEntry],
        "section_order": list[str],
    }
    SECTIONS: ClassVar[tuple[str, ...]] = tuple(SECTION_TYPES)
    DEFAULT_ORDER: ClassVar[tuple[str, ...]] = (
        "skills",
        "experience",
        "projects",
        "education",
    )

    contact: Contact = Field(default_factory=Contact)
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    section_order: list[str] = Field(default_factory=lambda: list(Resume.DEFAULT_ORDER))

    @classmethod
    def validate_section(cls, name: str, data: object) -> object:
        """Validate one section and return its JSON-compatible form."""
        if name not in cls.SECTION_TYPES:
            raise KeyError(name)
        adapter = TypeAdapter(cls.SECTION_TYPES[name])
        return adapter.dump_python(adapter.validate_python(data), mode="json")

    @classmethod
    def from_sections(cls, sections: dict[str, object]) -> "Resume":
        """Build a résumé from stored per-section JSON; missing ones default."""
        return cls.model_validate({k: v for k, v in sections.items() if k in cls.SECTIONS})

    def to_sections(self) -> dict[str, object]:
        data = self.model_dump(mode="json")
        return {name: data[name] for name in self.SECTIONS}

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_sections(), indent=indent, ensure_ascii=False)
