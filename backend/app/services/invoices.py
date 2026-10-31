from datetime import datetime, timezone
from email.message import EmailMessage
from io import BytesIO
import smtplib

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import Actor
from app.errors import ConflictError, NotFoundError, ValidationFailed
from app.models import Customer, Invoice, InvoiceLine, Payment
from app.schemas.contract import InvoiceOut


def list_for_customer(db: Session, customer_id: int, status: str | None = None) -> list[InvoiceOut]:
    query = select(Invoice).where(Invoice.customer_id == customer_id)
    if status:
        query = query.where(Invoice.status == status)
    return [
        InvoiceOut(id=row.id, number=row.number, customer_id=row.customer_id, status=row.status,
                   invoice_date=row.invoice_date, due_date=row.due_date, total=row.total, amount_due=row.amount_due)
        for row in db.scalars(query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()))
    ]


def list_invoices(db: Session, actor: Actor, page: int, page_size: int, status: str | None):
    query = select(Invoice)
    count = select(func.count()).select_from(Invoice)
    if actor.role == "customer":
        query = query.where(Invoice.customer_id == actor.customer_id)
        count = count.where(Invoice.customer_id == actor.customer_id)
    if status:
        query = query.where(Invoice.status == status)
        count = count.where(Invoice.status == status)
    rows = list(db.scalars(query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).offset((page - 1) * page_size).limit(page_size)))
    return [InvoiceOut(id=row.id, number=row.number, customer_id=row.customer_id, status=row.status,
                       invoice_date=row.invoice_date, due_date=row.due_date, total=row.total, amount_due=row.amount_due)
            for row in rows], db.scalar(count) or 0


def _get(db: Session, actor: Actor, invoice_id: int, *, lock: bool = False) -> Invoice:
    query = select(Invoice).where(Invoice.id == invoice_id)
    if actor.role == "customer":
        query = query.where(Invoice.customer_id == actor.customer_id)
    if lock:
        query = query.with_for_update()
    invoice = db.scalar(query)
    if invoice is None:
        raise NotFoundError("Invoice not found")
    return invoice


def get_invoice(db: Session, actor: Actor, invoice_id: int) -> Invoice:
    return _get(db, actor, invoice_id)


def confirm(db: Session, invoice_id: int) -> Invoice:
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if invoice is None:
        raise NotFoundError("Invoice not found")
    if invoice.status != "draft":
        raise ValidationFailed("Only draft invoices can be confirmed")
    invoice.status = "confirmed"
    db.commit()
    db.refresh(invoice)
    return invoice


def cancel(db: Session, invoice_id: int) -> Invoice:
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if invoice is None:
        raise NotFoundError("Invoice not found")
    if invoice.status not in {"draft", "confirmed"}:
        raise ValidationFailed("Only draft or confirmed invoices can be cancelled")
    if (db.scalar(select(func.count()).select_from(Payment).where(Payment.invoice_id == invoice.id)) or 0) > 0:
        raise ConflictError("Invoices with payments cannot be cancelled")
    from app.models import Discount

    discount_ids = set(db.scalars(
        select(InvoiceLine.discount_id).where(
            InvoiceLine.invoice_id == invoice.id, InvoiceLine.discount_id.is_not(None)
        )
    ))
    for discount_id in discount_ids:
        discount = db.scalar(select(Discount).where(Discount.id == discount_id).with_for_update())
        if discount is not None:
            discount.uses_count = max(0, discount.uses_count - 1)
    invoice.status = "cancelled"
    db.commit()
    db.refresh(invoice)
    return invoice


def invoice_pdf(db: Session, actor: Actor, invoice_id: int) -> bytes:
    invoice = _get(db, actor, invoice_id)
    customer = db.get(Customer, invoice.customer_id)
    lines = list(db.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id).order_by(InvoiceLine.id)))
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=letter)
    page.setTitle(f"Invoice {invoice.number}")
    page.setFont("Helvetica-Bold", 18)
    page.drawString(50, 750, f"Invoice {invoice.number}")
    page.setFont("Helvetica", 10)
    page.drawString(50, 730, f"Customer: {customer.name if customer else invoice.customer_id}")
    page.drawString(50, 715, f"Invoice date: {invoice.invoice_date.isoformat()}   Due: {invoice.due_date.isoformat()}")
    y = 680
    page.setFont("Helvetica-Bold", 10)
    page.drawString(50, y, "Description")
    page.drawString(330, y, "Qty")
    page.drawString(380, y, "Unit price")
    page.drawString(490, y, "Line total")
    y -= 18
    page.setFont("Helvetica", 9)
    for line in lines:
        if y < 75:
            page.showPage()
            y = 750
        page.drawString(50, y, line.description[:52])
        page.drawRightString(355, y, str(line.quantity))
        page.drawRightString(465, y, f"{line.unit_price + line.variant_extra:.2f}")
        page.drawRightString(560, y, f"{line.line_total:.2f}")
        y -= 16
    y -= 12
    page.drawRightString(560, y, f"Subtotal: {invoice.subtotal:.2f}")
    page.drawRightString(560, y - 15, f"Discounts: {invoice.discount_total:.2f}")
    page.drawRightString(560, y - 30, f"Tax: {invoice.tax_total:.2f}")
    page.setFont("Helvetica-Bold", 12)
    page.drawRightString(560, y - 52, f"Total: {invoice.total:.2f}")
    page.save()
    return buffer.getvalue()


def send_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice not found")
    if invoice.status != "confirmed":
        raise ValidationFailed("Only confirmed invoices can be sent")
    customer = db.get(Customer, invoice.customer_id)
    if customer is None or not customer.email:
        raise ValidationFailed("Invoice customer has no email address")
    message = EmailMessage()
    message["Subject"] = f"Revo invoice {invoice.number}"
    message["From"] = settings.smtp_from
    message["To"] = customer.email
    message.set_content(f"Please find invoice {invoice.number} attached. Amount due: {invoice.amount_due} {settings.app_currency}.")
    message.add_attachment(invoice_pdf(db, Actor(user_id=0, role="admin", customer_id=None), invoice_id),
                          maintype="application", subtype="pdf", filename=f"{invoice.number}.pdf")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as smtp:
        smtp.send_message(message)
    invoice.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invoice)
    return invoice


def pdf_filename(db: Session, actor: Actor, invoice_id: int) -> str:
    return f"{_get(db, actor, invoice_id).number}.pdf"
