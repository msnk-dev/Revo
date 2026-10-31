from collections.abc import Iterator
from dataclasses import dataclass
from typing import Callable, Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Actor:
    user_id: int
    role: Literal["admin", "staff", "customer"]
    customer_id: int | None


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_current_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Actor:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.app_secret_key, algorithms=["HS256"])
        user_id = int(payload["sub"])
        role = payload["role"]
        if role not in {"admin", "staff", "customer"}:
            raise ValueError("invalid role")
        customer_id = payload.get("customer_id")
        return Actor(user_id=user_id, role=role, customer_id=int(customer_id) if customer_id is not None else None)
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc


def require_roles(*roles: str) -> Callable[..., Actor]:
    def dependency(actor: Actor = Depends(get_current_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return actor

    return dependency

