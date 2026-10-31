from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.deps import Actor, get_current_actor, get_db, require_roles
from app.schemas.customers import CustomerCreateIn, CustomerListOut, CustomerOut
from app.services import customers as service

router = APIRouter(tags=["customers"])
DbSession = Annotated[Session, Depends(get_db)]
StaffActor = Annotated[Actor, Depends(require_roles("admin", "staff"))]
AnyActor = Annotated[Actor, Depends(get_current_actor)]


@router.get("/customers", response_model=CustomerListOut)
def list_customers(
    db: DbSession, actor: StaffActor,
    page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=100),
) -> CustomerListOut:
    items, total = service.list_customers(db, page, page_size, q)
    return CustomerListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreateIn, db: DbSession, actor: StaffActor) -> CustomerOut:
    return service.create_customer(db, payload)


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> CustomerOut:
    return service.get_customer(db, actor, customer_id)


@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: Annotated[int, Path(gt=0)], payload: CustomerCreateIn, db: DbSession, actor: StaffActor,
) -> CustomerOut:
    return service.update_customer(db, actor, customer_id, payload)


@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_customer(customer_id: Annotated[int, Path(gt=0)], db: DbSession, actor: Annotated[Actor, Depends(require_roles("admin"))]) -> Response:
    service.deactivate_customer(db, customer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
