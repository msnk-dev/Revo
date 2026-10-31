from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.deps import Actor, get_db, require_roles
from app.schemas.discounts import DiscountCreateIn, DiscountDetailOut, DiscountListOut
from app.services import discounts

router = APIRouter(tags=["discounts"])
DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Actor, Depends(require_roles("admin", "staff"))]
Admin = Annotated[Actor, Depends(require_roles("admin"))]


@router.get("/discounts", response_model=DiscountListOut)
def list_discounts(db: DbSession, actor: Reader, page: int = Query(default=1, ge=1),
                   page_size: int = Query(default=50, ge=1, le=100),
                   q: str | None = Query(default=None, min_length=1, max_length=100)) -> DiscountListOut:
    items, total = discounts.list_discounts(db, page, page_size, q)
    return DiscountListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/discounts/{discount_id}", response_model=DiscountDetailOut)
def get_discount(discount_id: Annotated[int, Path(gt=0)], db: DbSession, actor: Reader) -> DiscountDetailOut:
    return discounts.get_discount(db, discount_id)


@router.post("/discounts", response_model=DiscountDetailOut, status_code=status.HTTP_201_CREATED)
def create_discount(payload: DiscountCreateIn, db: DbSession, actor: Admin) -> DiscountDetailOut:
    return discounts.create_discount(db, payload)


@router.put("/discounts/{discount_id}", response_model=DiscountDetailOut)
def update_discount(discount_id: Annotated[int, Path(gt=0)], payload: DiscountCreateIn,
                    db: DbSession, actor: Admin) -> DiscountDetailOut:
    return discounts.update_discount(db, discount_id, payload)


@router.delete("/discounts/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_discount(discount_id: Annotated[int, Path(gt=0)], db: DbSession, actor: Admin) -> Response:
    discounts.deactivate_discount(db, discount_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
