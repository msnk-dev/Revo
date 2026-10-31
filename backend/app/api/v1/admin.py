from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.deps import Actor, get_db, require_roles
from app.schemas.auth import StaffCreateIn, StaffDeactivateIn, StaffListOut, StaffOut
from app.services import auth as auth_service

router = APIRouter(prefix="/admin", tags=["admin"])
DbSession = Annotated[Session, Depends(get_db)]
AdminActor = Annotated[Actor, Depends(require_roles("admin"))]


def _staff_out(user: object) -> StaffOut:
    return StaffOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreateIn, db: DbSession, actor: AdminActor) -> StaffOut:
    user = auth_service.create_staff(db, str(payload.email), payload.password, payload.name)
    return _staff_out(user)


@router.get("/staff", response_model=StaffListOut)
def list_staff(
    db: DbSession,
    actor: AdminActor,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> StaffListOut:
    items, total = auth_service.list_staff(db, page, page_size)
    return StaffListOut(
        items=[_staff_out(user) for user in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/staff/{staff_id}", response_model=StaffOut)
def deactivate_staff(
    staff_id: Annotated[int, Path(gt=0)],
    payload: StaffDeactivateIn,
    db: DbSession,
    actor: AdminActor,
) -> StaffOut:
    user = auth_service.deactivate_staff(db, staff_id)
    return _staff_out(user)

