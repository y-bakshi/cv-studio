"""Persist a ``Resume`` as one JSON row per section and load it back whole."""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CVDocument, CVSection, utcnow
from ..resume import Resume
from .revisions import snapshot_revision


def load_resume(db: Session, cv: CVDocument) -> Resume:
    rows = db.scalars(select(CVSection).where(CVSection.cv_id == cv.id)).all()
    return Resume.from_sections({row.name: json.loads(row.data_json) for row in rows})


def write_sections(db: Session, cv: CVDocument, sections: dict[str, object]) -> None:
    """Upsert only the given sections and bump the CV version once."""
    existing = {
        row.name: row
        for row in db.scalars(select(CVSection).where(CVSection.cv_id == cv.id))
    }
    for name, data in sections.items():
        payload = json.dumps(data, ensure_ascii=False)
        row = existing.get(name)
        if row is None:
            db.add(CVSection(cv_id=cv.id, name=name, data_json=payload))
        elif row.data_json != payload:
            row.data_json = payload
    cv.version += 1
    cv.updated_at = utcnow()
    snapshot_revision(db, cv)
