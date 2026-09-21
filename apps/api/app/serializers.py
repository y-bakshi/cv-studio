"""Explicit API serializers for database models.

Keeping response shaping here prevents accidental exposure of internal fields
such as artifact paths, password hashes, and ownership identifiers.
"""

import json

from .models import CVDocument, Compilation


def compilation_payload(item: Compilation | None) -> dict | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "cv_id": item.cv_id,
        "status": item.status,
        "log": item.log,
        "created_at": item.created_at,
        "finished_at": item.finished_at,
        "download_url": (
            f"/api/compilations/{item.id}/download"
            if item.status == "success"
            else None
        ),
    }


def cv_payload(
    cv: CVDocument,
    latest_compilation: Compilation | None = None,
) -> dict:
    return {
        "id": cv.id,
        "title": cv.title,
        "folder": cv.folder,
        "version": cv.version,
        "starred": cv.starred,
        "document": json.loads(cv.document_json),
        "tex_source": cv.tex_source,
        "updated_at": cv.updated_at,
        "latest_compilation": compilation_payload(latest_compilation),
    }
