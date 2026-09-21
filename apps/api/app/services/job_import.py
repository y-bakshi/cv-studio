"""Text extraction for supported job-description uploads."""

import io
from pathlib import Path

from fastapi import HTTPException, status
from pypdf import PdfReader

MAX_UPLOAD_BYTES = 2_000_000
MAX_CONTENT_CHARACTERS = 1_000_000
SUPPORTED_TEXT_SUFFIXES = {".txt", ".md"}


def extract_job_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in SUPPORTED_TEXT_SUFFIXES:
        content = data.decode("utf-8", errors="replace")
    elif suffix == ".pdf":
        content = "\n".join(
            page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages
        )
    else:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Use TXT, Markdown, or text-based PDF",
        )

    if not content.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No text could be extracted",
        )
    return content[:MAX_CONTENT_CHARACTERS]


# TODO(job-link-ingestion): Add a URL ingestion adapter with SSRF protection,
# explicit allow/deny rules, response-size limits, and sanitized HTML extraction.
