import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import Actor, get_current_actor, get_db
from app.schemas.auth import (
    AuthOut,
    ForgotPasswordIn,
    LoginIn,
    ResetPasswordIn,
    SignupIn,
)
from app.schemas.contract import ContractModel
from app.services import auth as auth_service

router = APIRouter(prefix="/auth")
DbSession = Annotated[Session, Depends(get_db)]


class MessageOut(ContractModel):
    message: str


def _set_session_cookies(response: Response, identity: auth_service.AuthIdentity) -> None:
    access_token, refresh_token = auth_service.create_tokens(identity, identity.token_version)
    secure = settings.app_env == "production"
    response.set_cookie(
        "access_token",
        access_token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1/auth",
    )
    response.set_cookie(
        "csrf_token",
        secrets.token_urlsafe(24),
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    secure = settings.app_env == "production"
    response.delete_cookie("access_token", path="/", secure=secure, httponly=True, samesite="lax")
    response.delete_cookie("refresh_token", path="/api/v1/auth", secure=secure, httponly=True, samesite="lax")
    response.delete_cookie("csrf_token", path="/", secure=secure, httponly=False, samesite="lax")


def _auth_out(identity: auth_service.AuthIdentity) -> AuthOut:
    return AuthOut(
        user_id=identity.user_id,
        email=identity.email,
        role=identity.role,
        customer_id=identity.customer_id,
    )


@router.post("/signup", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, response: Response, db: DbSession) -> AuthOut:
    identity = auth_service.signup(
        db,
        email=str(payload.email),
        password=payload.password,
        name=payload.name,
        company=payload.company,
        phone=payload.phone,
    )
    _set_session_cookies(response, identity)
    return _auth_out(identity)


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, request: Request, response: Response, db: DbSession) -> AuthOut:
    client_key = request.client.host if request.client is not None else "unknown"
    identity = auth_service.authenticate(db, str(payload.email), payload.password, client_key)
    _set_session_cookies(response, identity)
    return _auth_out(identity)


@router.post("/refresh", response_model=AuthOut)
def refresh(request: Request, response: Response, db: DbSession) -> AuthOut:
    token = request.cookies.get("refresh_token")
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing")
    identity, _token_version = auth_service.refresh_identity(db, token)
    _set_session_cookies(response, identity)
    return _auth_out(identity)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    actor: Actor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> Response:
    auth_service.invalidate_sessions(db, actor.user_id)
    _clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    response.body = b""
    return response


@router.post("/forgot", response_model=MessageOut, status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordIn, db: DbSession) -> MessageOut:
    auth_service.request_password_reset(db, str(payload.email))
    return MessageOut(message="If the account exists, reset instructions were sent.")


@router.post("/reset", response_model=MessageOut)
def reset_password(payload: ResetPasswordIn, db: DbSession) -> MessageOut:
    auth_service.reset_password(db, payload.token, payload.new_password)
    return MessageOut(message="Password reset successfully.")


@router.get("/me", response_model=AuthOut)
def me(actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)) -> AuthOut:
    return _auth_out(auth_service.current_identity(db, actor.user_id))

