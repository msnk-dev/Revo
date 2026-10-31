from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.deps import Actor, get_db, require_roles
from app.schemas.invoices import PaymentCreateIn, PaymentListOut
from app.services import payments

router = APIRouter(tags=["payments"])
DbSession = Annotated[Session, Depends(get_db)]
StaffActor = Annotated[Actor, Depends(require_roles("admin", "staff"))]


@router.post("/invoices/{invoice_id}/payments", status_code=status.HTTP_201_CREATED)
def create_payment(invoice_id: Annotated[int, Path(gt=0)], payload: PaymentCreateIn,
                   db: DbSession, actor: StaffActor):
    payment = payments.record_payment(db, invoice_id, payload, actor.user_id)
    return {"id": payment.id, "invoice_id": payment.invoice_id, "amount": payment.amount,
            "paid_on": payment.paid_on, "method_id": payment.method_id}


@router.get("/payments", response_model=PaymentListOut)
def list_payments(db: DbSession, actor: StaffActor, page: int = Query(default=1, ge=1),
                  page_size: int = Query(default=50, ge=1, le=100)) -> PaymentListOut:
    items, total = payments.list_payments(db, page, page_size)
    return PaymentListOut(items=items, total=total, page=page, page_size=page_size)
