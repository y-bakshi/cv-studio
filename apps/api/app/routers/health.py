import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {
        "ok": True,
        "database": "ok",
        "pdflatex": shutil.which("pdflatex") is not None,
    }
