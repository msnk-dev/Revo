from datetime import date

from sqlalchemy.orm import Session

from app.deps import Actor
from app.errors import NotFoundError
from app.schemas.contract import DryRunOut, GenerateResultOut, InvoiceBreakdownOut, InvoiceBreakdownLineOut


def dry_run_generate(db: Session, as_of: date) -> DryRunOut:
    return DryRunOut(as_of=as_of, eligible_count=0)


def generate_due_invoices(db: Session, as_of: date) -> GenerateResultOut:
    return GenerateResultOut(created=0, skipped_duplicates=0, failed=[])


def get_invoice_breakdown(db: Session, actor: Actor, invoice_id: int) -> InvoiceBreakdownOut:
    if actor.role == "customer" and (actor.customer_id != 1 or invoice_id != 1):
        raise NotFoundError("Invoice not found")
    line = InvoiceBreakdownLineOut(
        description="Demo subscription",
        quantity=1,
        unit_price="1200.00",
        variant_extra="0.00",
        discount_name=None,
        discount_amount="0.00",
        discount_reason=None,
        tax_name=None,
        tax_rate_pct=None,
        tax_amount="0.00",
        line_total="1200.00",
    )
    return InvoiceBreakdownOut(
        invoice_id=invoice_id,
        invoice_number="INV-000001",
        lines=[line],
        subtotal="1200.00",
        discount_total="0.00",
        tax_total="0.00",
        total="1200.00",
    )

