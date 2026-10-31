import hashlib
import logging
import secrets
import smtplib
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AuthenticationError, ConflictError, NotFoundError, RateLimitExceeded, ValidationFailed
from app.models import Customer, PasswordResetToken, User
from app.services.email import send_plain

logger = logging.getLogger(__name__)
password_hasher = PasswordHasher()
dummy_password_hash = password_hasher.hash("RevoDummyPassword7!")
_login_failures: dict[str, deque[float]] = {}
_login_lock = threading.Lock()
_LOGIN_WINDOW_SECONDS = 15 * 60
_LOGIN_FAILURE_LIMIT = 5


@dataclass(frozen=True)
class AuthIdentity:
    user_id: int
    email: str
    role: str
    customer_id: int | None
    token_version: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> None:
    missing = []
    if len(password) < 9:
        missing.append("at least 9 characters")
    if not any(char.isupper() for char in password):
        missing.append("an uppercase letter")
    if not any(char.islower() for char in password):
        missing.append("a lowercase letter")
    if not any(not char.isalnum() for char in password):
        missing.append("a special character")
    if missing:
        raise ValidationFailed("Password does not meet the requirements", {"password": ", ".join(missing)})


def _identity(db: Session, user: User) -> AuthIdentity:
    customer_id = db.scalar(select(Customer.id).where(Customer.user_id == user.id))
    return AuthIdentity(
        user_id=user.id,
        email=user.email,
        role=user.role,
        customer_id=customer_id,
        token_version=user.token_version,
    )


def signup(
    db: Session,
    email: str,
    password: str,
    name: str,
    company: str | None = None,
    phone: str | None = None,
) -> AuthIdentity:
    normalized_email = _normalized_email(email)
    validate_password(password)
    if db.scalar(select(User.id).where(func.lower(User.email) == normalized_email)) is not None:
        raise ConflictError("An account with this email already exists", {"email": "Already registered"})

    user = User(
        email=normalized_email,
        name=name.strip(),
        password_hash=password_hasher.hash(password),
        role="customer",
        is_active=True,
    )
    db.add(user)
    db.flush()
    customer = Customer(
        user_id=user.id,
        name=name.strip(),
        email=normalized_email,
        company=company,
        phone=phone,
        is_active=True,
    )
    db.add(customer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("An account with this email already exists", {"email": "Already registered"}) from exc
    db.refresh(user)
    return _identity(db, user)


def _prune_failures(key: str, now: float) -> deque[float]:
    attempts = _login_failures.get(key, deque())
    while attempts and now - attempts[0] >= _LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    if attempts:
        _login_failures[key] = attempts
    else:
        _login_failures.pop(key, None)
    return attempts


def _check_login_attempts(key: str) -> None:
    with _login_lock:
        attempts = _prune_failures(key, time.monotonic())
        if len(attempts) >= _LOGIN_FAILURE_LIMIT:
            raise RateLimitExceeded("Too many failed login attempts. Try again in 15 minutes.")


def _record_failed_login(key: str) -> None:
    with _login_lock:
        attempts = _prune_failures(key, time.monotonic())
        attempts.append(time.monotonic())
        _login_failures[key] = attempts


def authenticate(db: Session, email: str, password: str, client_key: str) -> AuthIdentity:
    normalized_email = _normalized_email(email)
    key = f"{client_key}:{normalized_email}"
    _check_login_attempts(key)
    user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    stored_hash = user.password_hash if user is not None else dummy_password_hash
    try:
        valid_password = password_hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        valid_password = False
    if user is None or not user.is_active or not valid_password:
        _record_failed_login(key)
        raise AuthenticationError("Invalid email or password")

    with _login_lock:
        _login_failures.pop(key, None)
    user.last_login_at = _now()
    db.commit()
    db.refresh(user)
    return _identity(db, user)


def create_tokens(identity: AuthIdentity, token_version: int) -> tuple[str, str]:
    now = _now()
    common = {
        "sub": str(identity.user_id),
        "role": identity.role,
        "customer_id": identity.customer_id,
        "ver": token_version,
        "iat": now,
    }
    access = jwt.encode(
        {
            **common,
            "jti": secrets.token_urlsafe(16),
            "type": "access",
            "exp": now + timedelta(minutes=settings.access_token_minutes),
        },
        settings.app_secret_key,
        algorithm="HS256",
    )
    refresh = jwt.encode(
        {
            **common,
            "jti": secrets.token_urlsafe(16),
            "type": "refresh",
            "exp": now + timedelta(days=settings.refresh_token_days),
        },
        settings.app_secret_key,
        algorithm="HS256",
    )
    return access, refresh


def refresh_identity(db: Session, token: str) -> tuple[AuthIdentity, int]:
    try:
        claims = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
        if claims.get("type") != "refresh":
            raise ValueError("wrong token type")
        user_id = int(claims["sub"])
        token_version = int(claims["ver"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError("Refresh token is invalid or expired") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != token_version:
        raise AuthenticationError("Refresh token is invalid or expired")
    return _identity(db, user), user.token_version


def current_identity(db: Session, user_id: int) -> AuthIdentity:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User is inactive or no longer exists")
    return _identity(db, user)


def invalidate_sessions(db: Session, user_id: int) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("User is inactive or no longer exists")
    user.token_version += 1
    db.commit()


def request_password_reset(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(func.lower(User.email) == _normalized_email(email), User.is_active.is_(True)))
    if user is None:
        return

    now = _now()
    for old_token in db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    ):
        old_token.used_at = now

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=60),
        )
    )
    db.commit()
    try:
        send_plain(
            to=user.email,
            subject="Reset your Revo password",
            body=f"Use this single-use token to reset your Revo password within 60 minutes:\n\n{raw_token}",
        )
    except (OSError, smtplib.SMTPException):
        logger.exception("Password reset email could not be delivered")


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    validate_password(new_password)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    reset_token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        ).with_for_update()
    )
    if reset_token is None:
        raise ValidationFailed("Reset token is invalid or expired", {"token": "Invalid or expired token"})
    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    now = _now()
    if expires_at <= now:
        raise ValidationFailed("Reset token is invalid or expired", {"token": "Invalid or expired token"})

    user = db.get(User, reset_token.user_id)
    if user is None or not user.is_active:
        raise ValidationFailed("Reset token is invalid or expired", {"token": "Invalid or expired token"})
    user.password_hash = password_hasher.hash(new_password)
    user.token_version += 1
    for token in db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    ):
        token.used_at = now
    db.commit()


def create_staff(db: Session, email: str, password: str, name: str) -> User:
    normalized_email = _normalized_email(email)
    validate_password(password)
    if db.scalar(select(User.id).where(func.lower(User.email) == normalized_email)) is not None:
        raise ConflictError("An account with this email already exists", {"email": "Already registered"})
    user = User(
        email=normalized_email,
        name=name.strip(),
        password_hash=password_hasher.hash(password),
        role="staff",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("An account with this email already exists", {"email": "Already registered"}) from exc
    db.refresh(user)
    return user


def list_staff(db: Session, page: int, page_size: int) -> tuple[list[User], int]:
    base = select(User).where(User.role == "staff").order_by(User.id)
    total = db.scalar(select(func.count()).select_from(User).where(User.role == "staff")) or 0
    items = list(db.scalars(base.offset((page - 1) * page_size).limit(page_size)))
    return items, total


def deactivate_staff(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.role != "staff":
        raise NotFoundError("Staff user not found")
    user.is_active = False
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user

