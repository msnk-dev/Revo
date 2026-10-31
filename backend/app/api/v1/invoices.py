from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from fastapi.responses import Response as RawResponse
from sqlalchemy.orm import Session

from app.deps import Actor, get_current_actor, get_db, require_roles
from app.schemas.contract import DryRunOut, GenerateResultOut, InvoiceBreakdownOut
from app.schemas.invoices import InvoiceGenerateOut, InvoiceListOut
from app.services import billing, invoices

router = APIRouter(tags=["invoices"])
DbSession = Annotated[Session, Depends(get_db)]
AnyActor = Annotated[Actor, Depends(get_current_actor)]
StaffActor = Annotated[Actor, Depends(require_roles("admin", "staff"))]


@router.get("/invoices", response_model=InvoiceListOut)
def list_invoices(db: DbSession, actor: AnyActor, page: int = Query(default=1, ge=1),
                  page_size: int = Query(default=50, ge=1, le=100),
                  status_filter: str | None = Query(default=None, alias="status")) -> InvoiceListOut:
    items, total = invoices.list_invoices(db, actor, page, page_size, status_filter)
    return InvoiceListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/invoices/generate", response_model=InvoiceGenerateOut)
def generate_invoices(db: DbSession, actor: StaffActor, as_of: date = Query(default_factory=date.today),
                      dry_run: bool = Query(default=False)) -> InvoiceGenerateOut:
    if dry_run:
        result = billing.dry_run_generate(db, as_of)
        return InvoiceGenerateOut(dry_run=True, as_of=as_of, eligible_count=result.eligible_count)
    result = billing.generate_due_invoices(db, as_of)
    return InvoiceGenerateOut(dry_run=False, as_of=as_of, created=result.created,
                              skipped_duplicates=result.skipped_duplicates, failed=[item.model_dump() for item in result.failed])


@router.get("/invoices/{invoice_id}", response_model=InvoiceBreakdownOut)
def get_invoice(invoice_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> InvoiceBreakdownOut:
    return billing.get_invoice_breakdown(db, actor, invoice_id)


@router.post("/invoices/{invoice_id}/confirm")
def confirm_invoice(invoice_id: Annotated[int, Path(gt=0)], db: DbSession, actor: StaffActor):
    row = invoices.confirm(db, invoice_id)
    return {"id": row.id, "number": row.number, "status": row.status}


@router.post("/invoices/{invoice_id}/cancel")
def cancel_invoice(invoice_id: Annotated[int, Path(gt=0)], db: DbSession, actor: StaffActor):
    row = invoices.cancel(db, invoice_id)
    return {"id": row.id, "number": row.number, "status": row.status}


@router.post("/invoices/{invoice_id}/send")
def send_invoice(invoice_id: Annotated[int, Path(gt=0)], db: DbSession, actor: StaffActor):
    row = invoices.send_invoice(db, invoice_id)
    return {"id": row.id, "number": row.number, "status": row.status, "sent_at": row.sent_at}


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: Annotated[int, Path(gt=0)], db: DbSession, actor: AnyActor) -> RawResponse:
    content = invoices.invoice_pdf(db, actor, invoice_id)
    return RawResponse(content=content, media_type="application/pdf",
                       headers={"Content-Disposition": f'inline; filename="{invoices.pdf_filename(db, actor, invoice_id)}"'})
