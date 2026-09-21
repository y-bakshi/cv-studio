from sqlalchemy.orm import Session

from ..models import CVDocument, CVRevision


def snapshot_revision(db: Session, cv: CVDocument) -> CVRevision:
    """Add an immutable snapshot of the current CV state to the transaction."""
    revision = CVRevision(
        cv_id=cv.id,
        user_id=cv.user_id,
        version=cv.version,
        document_json=cv.document_json,
        tex_source=cv.tex_source,
    )
    db.add(revision)
    return revision
