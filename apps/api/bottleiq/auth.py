import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from bottleiq.config import settings
from bottleiq.db import get_db
from bottleiq.models import AuthSession, OrganizationMember, Store, User

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash("not-a-real-account-password")
COOKIE = "bottleiq_session"


@dataclass
class Actor:
    user: User
    organization_id: str
    role: str


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=token_digest(token),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(hours=12),
        )
    )
    db.commit()
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings().cookie_secure,
        samesite="lax",
        max_age=43200,
        path="/",
    )


def current_actor(request: Request, db: Session = Depends(get_db)) -> Actor:
    token = request.cookies.get(COOKIE)
    session = db.get(AuthSession, token_digest(token)) if token else None
    if session is None or session.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        raise HTTPException(401, "Please sign in to continue")
    user = db.get(User, session.user_id)
    member = db.scalar(
        select(OrganizationMember).where(OrganizationMember.user_id == session.user_id)
    )
    if not user or not member:
        raise HTTPException(401, "Account is not associated with an organization")
    return Actor(user, member.organization_id, member.role)


def editor(actor: Actor = Depends(current_actor)) -> Actor:
    if actor.role not in ("owner", "admin"):
        raise HTTPException(403, "An owner or admin must make this change")
    return actor


def get_store(db: Session, actor: Actor, store_id: str) -> Store:
    store = db.scalar(
        select(Store).where(Store.id == store_id, Store.organization_id == actor.organization_id)
    )
    if store is None:
        raise HTTPException(404, "Store not found")
    return store
