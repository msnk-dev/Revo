from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError, ValidationFailed
from app.models import Invoice, Payment, PaymentMethod
from app.schemas.invoices import PaymentCreateIn


def record_payment(db: Session, invoice_id: int, payload: PaymentCreateIn, actor_id: int) -> Payment:
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if invoice is None:
        raise NotFoundError("Invoice not found")
    if invoice.status != "confirmed":
        raise ValidationFailed("Only confirmed invoices accept payments")
    method = db.get(PaymentMethod, payload.method_id)
    if method is None or not method.is_active:
        raise ValidationFailed("Payment method is unavailable", {"method_id": "Unknown or inactive method"})
    amount = payload.amount.quantize(Decimal("0.01"))
    if amount > invoice.amount_due:
        raise ValidationFailed("Payment exceeds the outstanding amount", {"amount": f"Maximum payment is {invoice.amount_due}"})
    payment = Payment(invoice_id=invoice.id, method_id=method.id, amount=amount, paid_on=payload.paid_on,
                      note=payload.note, recorded_by=actor_id)
    db.add(payment)
    invoice.amount_paid = (invoice.amount_paid + amount).quantize(Decimal("0.01"))
    invoice.amount_due = (invoice.total - invoice.amount_paid).quantize(Decimal("0.01"))
    if invoice.amount_due == Decimal("0.00"):
        invoice.status = "paid"
    db.commit()
    db.refresh(payment)
    return payment


def list_payments(db: Session, page: int, page_size: int, customer_id: int | None = None):
    query = select(Payment).join(Invoice, Invoice.id == Payment.invoice_id)
    count = select(func.count()).select_from(Payment).join(Invoice, Invoice.id == Payment.invoice_id)
    if customer_id is not None:
        query = query.where(Invoice.customer_id == customer_id)
        count = count.where(Invoice.customer_id == customer_id)
    rows = list(db.scalars(query.order_by(Payment.paid_on.desc(), Payment.id.desc()).offset((page - 1) * page_size).limit(page_size)))
    items = []
    for row in rows:
        method = db.get(PaymentMethod, row.method_id)
        items.append({"id": row.id, "invoice_id": row.invoice_id, "amount": row.amount,
                      "paid_on": row.paid_on, "method": method.name if method else "unknown"})
    return items, db.scalar(count) or 0
