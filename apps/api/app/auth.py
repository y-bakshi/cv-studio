from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DBSession

from .config import settings
from .database import get_db
from .models import Session, User


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt_hex, expected = encoded.split("$", 2)
        actual = hash_password(password, bytes.fromhex(salt_hex)).split("$", 2)[2]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: DBSession, user: User, response: Response) -> None:
    raw = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    db.add(Session(user_id=user.id, token_hash=token_digest(raw), expires_at=expires))
    db.commit()
    response.set_cookie(
        settings.session_cookie,
        raw,
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def clear_session(db: DBSession, response: Response, raw: str | None) -> None:
    if raw:
        db.execute(delete(Session).where(Session.token_hash == token_digest(raw)))
        db.commit()
    response.delete_cookie(settings.session_cookie, path="/")


async def current_user(
    raw: str | None = Cookie(default=None, alias=settings.session_cookie),
    db: DBSession = Depends(get_db),
) -> User:
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    row = db.execute(
        select(Session, User)
        .join(User, User.id == Session.user_id)
        .where(Session.token_hash == token_digest(raw))
    ).first()
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    session, user = row
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return user
