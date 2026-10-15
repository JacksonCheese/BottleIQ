import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bottleiq.auth import (
    COOKIE,
    DUMMY_HASH,
    Actor,
    as_utc,
    current_actor,
    login_session,
    passwords,
    token_digest,
)
from bottleiq.config import settings
from bottleiq.db import get_db
from bottleiq.emailer import send_account_email
from bottleiq.models import (
    AuthSession,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    PasswordReset,
    User,
)
from bottleiq.rate_limit import limit_auth
from bottleiq.schemas import (
    Credentials,
    InvitationAccept,
    InvitationInput,
    PasswordResetInput,
    RecoveryRequest,
    Signup,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", status_code=201)
def signup(data: Signup, response: Response, db: Session = Depends(get_db)) -> dict:
    limit_auth(db, "signup", str(data.email), limit=5, seconds=3600)
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
    limit_auth(db, "login", str(data.email), limit=20, seconds=60)
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


@router.post("/recovery/request")
def request_recovery(data: RecoveryRequest, db: Session = Depends(get_db)) -> dict:
    """The same response is returned for known and unknown addresses."""
    if not settings().smtp_host:
        raise HTTPException(
            503, "Password recovery is temporarily unavailable. Contact pilot support."
        )
    limit_auth(db, "recovery", str(data.email), limit=5, seconds=3600)
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user and user.email != "demo@bottleiq.local":
        token = secrets.token_urlsafe(32)
        reset = PasswordReset(
            token_hash=token_digest(token),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        db.add(reset)
        db.commit()
        link = f"{settings().web_origin}/reset-password?token={quote(token)}"
        try:
            send_account_email(
                user.email,
                "Reset your BottleIQ password",
                f"Use this link within 30 minutes:\n{link}\n\nIf you did not request this, ignore this message.",
            )
        except (OSError, RuntimeError):
            db.delete(reset)
            db.commit()
            raise HTTPException(
                503, "Password recovery is temporarily unavailable. Contact pilot support."
            ) from None
    return {"message": "If this address has an account, a reset link has been sent."}


@router.post("/recovery/reset")
def reset_password(data: PasswordResetInput, db: Session = Depends(get_db)) -> dict:
    reset = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.token_hash == token_digest(data.token))
        .with_for_update()
    )
    if not reset or as_utc(reset.expires_at) <= datetime.now(UTC):
        raise HTTPException(400, "This reset link is invalid or expired. Request a new one.")
    user = db.get(User, reset.user_id)
    if not user:
        raise HTTPException(400, "This reset link is invalid or expired. Request a new one.")
    user.password_hash = passwords.hash(data.password)
    for session in db.scalars(select(AuthSession).where(AuthSession.user_id == user.id)):
        db.delete(session)
    for old_reset in db.scalars(select(PasswordReset).where(PasswordReset.user_id == user.id)):
        db.delete(old_reset)
    db.commit()
    return {"message": "Password changed. Sign in with your new password."}


@router.post("/invitations", status_code=201)
def invite(
    data: InvitationInput, actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> dict:
    if actor.role != "owner" or actor.user.email == "demo@bottleiq.local":
        raise HTTPException(403, "Only a live organization owner can invite staff")
    email = str(data.email).lower()
    limit_auth(db, "invite", email, limit=5, seconds=3600)
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(
            409, "This email already has a BottleIQ account. Contact pilot support."
        )
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=actor.organization_id,
        email=email,
        role=data.role,
        token_hash=token_digest(token),
        invited_by_user_id=actor.user.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    link = f"{settings().web_origin}/accept-invitation?token={quote(token)}"
    try:
        send_account_email(
            email,
            "Join your BottleIQ organization",
            f"{actor.user.name} invited you as {data.role}. Use this link within 7 days:\n{link}\n\nIf you did not expect this, ignore this message.",
        )
    except (OSError, RuntimeError):
        db.delete(invitation)
        db.commit()
        raise HTTPException(503, "Invitation email could not be sent. Try again later.") from None
    return {
        "id": invitation.id,
        "email": email,
        "role": invitation.role,
        "expires_at": invitation.expires_at,
    }


@router.get("/invitations")
def list_invitations(
    actor: Actor = Depends(current_actor), db: Session = Depends(get_db)
) -> list[dict]:
    if actor.role != "owner":
        raise HTTPException(403, "Only the organization owner can view invitations")
    return [
        {
            "id": item.id,
            "email": item.email,
            "role": item.role,
            "expires_at": item.expires_at,
            "accepted_at": item.accepted_at,
        }
        for item in db.scalars(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == actor.organization_id)
            .order_by(OrganizationInvitation.created_at.desc())
            .limit(100)
        )
    ]


@router.post("/invitations/accept", status_code=201)
def accept_invitation(
    data: InvitationAccept, response: Response, db: Session = Depends(get_db)
) -> dict:
    invitation = db.scalar(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.token_hash == token_digest(data.token))
        .with_for_update()
    )
    if (
        not invitation
        or invitation.accepted_at
        or as_utc(invitation.expires_at) <= datetime.now(UTC)
    ):
        raise HTTPException(
            400, "This invitation is invalid or expired. Ask the owner for a new one."
        )
    user = User(email=invitation.email, name=data.name, password_hash=passwords.hash(data.password))
    db.add(user)
    try:
        db.flush()
        db.add(
            OrganizationMember(
                organization_id=invitation.organization_id, user_id=user.id, role=invitation.role
            )
        )
        invitation.accepted_at = datetime.now(UTC)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409, "This email already has an account. Contact pilot support."
        ) from exc
    login_session(db, user, response)
    return {"name": user.name, "role": invitation.role}
