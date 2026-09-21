"""Compilation queue orchestration.

The bounded executor keeps pdflatex off request threads for local development.
Production should replace this module's queue boundary with a durable worker.
"""

from concurrent.futures import ThreadPoolExecutor

from ..config import settings
from ..database import SessionLocal
from ..latex import compile_tex
from ..models import CVRevision, Compilation, utcnow

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="latex")


def submit_compilation(compilation_id: str) -> None:
    _executor.submit(_run_compilation, compilation_id)


def shutdown_compiler() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)


def _run_compilation(compilation_id: str) -> None:
    with SessionLocal() as db:
        item = db.get(Compilation, compilation_id)
        if item is None:
            return
        revision = db.get(CVRevision, item.revision_id)
        if revision is None:
            item.status = "failed"
            item.log = "The source revision no longer exists."
            item.finished_at = utcnow()
            db.commit()
            return

        item.status = "compiling"
        db.commit()
        output = (
            settings.artifact_root
            / item.user_id
            / item.cv_id
            / f"{item.id}.pdf"
        )
        success, log = compile_tex(revision.tex_source, output)
        item.status = "success" if success else "failed"
        item.log = log[-50_000:]
        item.finished_at = utcnow()
        item.artifact_path = str(output) if success else None
        db.commit()


# TODO(durable-compilation): Move this boundary to a Redis-backed worker and run
# TeX inside a network-disabled, resource-limited container before production.
