from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bottleiq.auth import (
    COOKIE,
    DUMMY_HASH,
    Actor,
    current_actor,
    login_session,
    passwords,
    token_digest,
)
from bottleiq.config import settings
from bottleiq.db import get_db
from bottleiq.models import AuthSession, Organization, OrganizationMember, User
from bottleiq.schemas import Credentials, Signup

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", status_code=201)
def signup(data: Signup, response: Response, db: Session = Depends(get_db)) -> dict:
    user = User(
        email=str(data.email).lower(), name=data.name, password_hash=passwords.hash(data.password)
    )
    org = Organization(name=data.organization_name)
    db.add_all([user, org])
    try:
        db.flush()
        db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists") from exc
    login_session(db, user, response)
    return {"name": user.name, "organization_id": org.id}


@router.post("/login")
def login(data: Credentials, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = passwords.verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Email or password is incorrect")
    login_session(db, user, response)
    return {"name": user.name}


@router.post("/demo")
def demo(response: Response, db: Session = Depends(get_db)) -> dict:
    if not settings().demo_enabled:
        raise HTTPException(404, "Demo mode is disabled")
    user = db.scalar(select(User).where(User.email == "demo@bottleiq.local"))
    if not user:
        raise HTTPException(503, "Demo is not seeded. Run make seed first.")
    login_session(db, user, response)
    return {"name": user.name}


@router.get("/me")
def me(actor: Actor = Depends(current_actor)) -> dict:
    return {
        "name": actor.user.name,
        "email": actor.user.email,
        "organization_id": actor.organization_id,
        "role": actor.role,
        "demo": actor.user.email == "demo@bottleiq.local",
    }


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    token = request.cookies.get(COOKIE)
    session = db.get(AuthSession, token_digest(token)) if token else None
    if session:
        db.delete(session)
        db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
