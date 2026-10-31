from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.deps import Actor, get_db, require_roles
from app.errors import NotFoundError
from app.schemas.invoices import InvoiceListOut, PaymentListOut
from app.schemas.subscriptions import SubscriptionListOut
from app.services import invoices, subscriptions
from app.services import payments

router = APIRouter(prefix="/portal", tags=["customer portal"])
DbSession = Annotated[Session, Depends(get_db)]
CustomerActor = Annotated[Actor, Depends(require_roles("customer"))]


def _customer_id(actor: Actor) -> int:
    if actor.customer_id is None:
        raise NotFoundError("Customer account not found")
    return actor.customer_id


@router.get("/subscriptions")
def my_subscriptions(db: DbSession, actor: CustomerActor, page: int = Query(default=1, ge=1),
                     page_size: int = Query(default=50, ge=1, le=100)) -> SubscriptionListOut:
    items, total = subscriptions.list_subscriptions(db, actor, page, page_size, None)
    return SubscriptionListOut(items=subscriptions.as_detail_list(db, items), total=total, page=page, page_size=page_size)


@router.get("/invoices")
def my_invoices(db: DbSession, actor: CustomerActor, status: str | None = None,
                page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100)) -> InvoiceListOut:
    items, total = invoices.list_invoices(db, actor, page, page_size, status)
    return InvoiceListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/payments")
def my_payments(db: DbSession, actor: CustomerActor, page: int = Query(default=1, ge=1),
                page_size: int = Query(default=50, ge=1, le=100)) -> PaymentListOut:
    items, total = payments.list_payments(db, page, page_size, _customer_id(actor))
    return PaymentListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/invoices/{invoice_id}/pdf")
def my_invoice_pdf(invoice_id: Annotated[int, Path(gt=0)], db: DbSession, actor: CustomerActor):
    filename = invoices.pdf_filename(db, actor, invoice_id)
    content = invoices.invoice_pdf(db, actor, invoice_id)
    return Response(content=content, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})
