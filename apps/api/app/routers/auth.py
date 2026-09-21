from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (
    clear_session,
    create_session,
    current_user,
    hash_password,
    verify_password,
)
from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import Credentials

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=201)
async def register(
    credentials: Credentials,
    response: Response,
    db: Session = Depends(get_db),
):
    email = credentials.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account already exists")

    user = User(email=email, password_hash=hash_password(credentials.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    create_session(db, user, response)
    return {"id": user.id, "email": user.email}


@router.post("/login")
async def login(
    credentials: Credentials,
    response: Response,
    db: Session = Depends(get_db),
):
    email = credentials.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
        )
    create_session(db, user, response)
    return {"id": user.id, "email": user.email}


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    clear_session(
        db,
        response,
        request.cookies.get(settings.session_cookie),
    )


@router.get("/me")
async def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}
