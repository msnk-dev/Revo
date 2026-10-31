from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import logging

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import Actor
from app.errors import NotFoundError
from app.models import (
    Discount, DiscountProduct, Invoice, InvoiceLine, Plan,
    Subscription, SubscriptionLine, SubscriptionLineVariant, Tax,
)
from app.schemas.contract import DryRunOut, GenerateResultOut, InvoiceBreakdownOut, InvoiceBreakdownLineOut

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
logger = logging.getLogger(__name__)


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def advance(period_start: date, period: str, anchor: date) -> date:
    if period == "daily":
        return period_start + timedelta(days=1)
    if period == "weekly":
        return period_start + timedelta(days=7)
    step = relativedelta(months=1 if period == "monthly" else 12)
    count = 1
    while True:
        candidate = anchor + step * count
        if candidate > period_start:
            return candidate
        count += 1


def _eligible_query(as_of: date):
    return select(Subscription.id).where(
        Subscription.status == "active",
        Subscription.is_paused.is_(False),
        Subscription.next_invoice_date.is_not(None),
        Subscription.next_invoice_date <= as_of,
        (Subscription.expiry_date.is_(None)) | (Subscription.next_invoice_date <= Subscription.expiry_date),
    ).order_by(Subscription.id)


def dry_run_generate(db: Session, as_of: date) -> DryRunOut:
    count = db.scalar(select(func.count()).select_from(Subscription).where(
        Subscription.status == "active", Subscription.is_paused.is_(False),
        Subscription.next_invoice_date.is_not(None), Subscription.next_invoice_date <= as_of,
        (Subscription.expiry_date.is_(None)) | (Subscription.next_invoice_date <= Subscription.expiry_date),
    )) or 0
    return DryRunOut(as_of=as_of, eligible_count=count)


def _best_discount(db: Session, product_id: int, quantity: int, gross: Decimal, as_of: date):
    discounts = list(
        db.scalars(
            select(Discount).where(
                Discount.is_active.is_(True),
                (Discount.start_date.is_(None)) | (Discount.start_date <= as_of),
                (Discount.end_date.is_(None)) | (Discount.end_date >= as_of),
                (Discount.max_uses.is_(None)) | (Discount.uses_count < Discount.max_uses),
                Discount.min_quantity <= quantity,
                Discount.min_purchase <= gross,
            ).with_for_update()
        )
    )
    candidates = []
    for discount in discounts:
        if discount.scope == "product":
            linked = db.scalar(
                select(DiscountProduct.id).where(
                    DiscountProduct.discount_id == discount.id,
                    DiscountProduct.product_id == product_id,
                )
            )
            if linked is None:
                continue
        saving = gross * discount.value / Decimal("100") if discount.type == "percent" else discount.value
        saving = min(_money(saving), gross)
        if saving > ZERO:
            candidates.append((saving, discount))
    return max(candidates, key=lambda item: (item[0], -item[1].id), default=(ZERO, None))


def _variant_extra(db: Session, line: SubscriptionLine) -> Decimal:
    from app.models import ProductVariantValue

    value = db.scalar(
        select(func.coalesce(func.sum(ProductVariantValue.extra_price), 0))
        .select_from(SubscriptionLineVariant)
        .join(ProductVariantValue, ProductVariantValue.id == SubscriptionLineVariant.variant_value_id)
        .where(SubscriptionLineVariant.line_id == line.id)
    )
    return _money(Decimal(value or 0))


def _make_invoice(db: Session, sub: Subscription, plan: Plan, as_of: date, period_start: date) -> Invoice:
    period_next = advance(period_start, plan.billing_period, sub.start_date)
    period_end = period_next - timedelta(days=1)
    invoice = Invoice(
        number="pending",
        subscription_id=sub.id,
        customer_id=sub.customer_id,
        status="draft",
        invoice_date=as_of,
        due_date=as_of + timedelta(days=sub.payment_terms_days),
        period_start=period_start,
        period_end=period_end,
        subtotal=ZERO,
        discount_total=ZERO,
        tax_total=ZERO,
        total=ZERO,
        amount_paid=ZERO,
        amount_due=ZERO,
    )
    db.add(invoice)
    db.flush()
    invoice.number = f"INV-{invoice.id:06d}"
    sub_lines = list(db.scalars(select(SubscriptionLine).where(SubscriptionLine.subscription_id == sub.id).order_by(SubscriptionLine.id)))
    subtotal = discount_total = tax_total = ZERO
    used_discount_ids: set[int] = set()
    for sub_line in sub_lines:
        variant_extra = _variant_extra(db, sub_line)
        full_unit = _money(sub_line.unit_price)
        unit_base = _money(full_unit - variant_extra)
        gross = _money(full_unit * sub_line.quantity)
        saving, discount = _best_discount(db, sub_line.product_id, sub_line.quantity, gross, as_of)
        taxable = _money(gross - saving)
        tax = db.get(Tax, sub_line.tax_id) if sub_line.tax_id is not None else None
        tax_rate = tax.rate_pct if tax is not None else None
        tax_name = tax.name if tax is not None else None
        tax_amount = _money(taxable * tax_rate / Decimal("100")) if tax_rate is not None else ZERO
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                product_id=sub_line.product_id,
                description=sub_line.description,
                quantity=sub_line.quantity,
                unit_price=unit_base,
                variant_extra=variant_extra,
                discount_id=discount.id if discount else None,
                discount_name=discount.name if discount else None,
                discount_reason=(f"{discount.type} discount: {discount.value}" if discount else None),
                discount_amount=saving,
                tax_name=tax_name,
                tax_rate_pct=tax_rate,
                tax_amount=tax_amount,
                line_total=_money(taxable + tax_amount),
            )
        )
        subtotal += gross
        discount_total += saving
        tax_total += tax_amount
        if discount is not None:
            used_discount_ids.add(discount.id)
    invoice.subtotal = _money(subtotal)
    invoice.discount_total = _money(discount_total)
    invoice.tax_total = _money(tax_total)
    invoice.total = _money(invoice.subtotal - invoice.discount_total + invoice.tax_total)
    invoice.amount_due = invoice.total
    for discount_id in used_discount_ids:
        discount = db.scalar(select(Discount).where(Discount.id == discount_id).with_for_update())
        if discount is not None:
            discount.uses_count += 1
    sub.next_invoice_date = period_next
    return invoice


def generate_due_invoices(db: Session, as_of: date) -> GenerateResultOut:
    created = skipped = 0
    failed = []
    last_id = 0
    while True:
        ids = list(db.scalars(_eligible_query(as_of).where(Subscription.id > last_id).limit(100)))
        if not ids:
            break
        last_id = ids[-1]
        for sub_id in ids:
            try:
                sub = db.scalar(select(Subscription).where(Subscription.id == sub_id).with_for_update(skip_locked=True))
                if sub is None or sub.status != "active" or sub.is_paused or sub.next_invoice_date is None:
                    db.rollback()
                    continue
                plan = db.get(Plan, sub.plan_id)
                if plan is None:
                    raise ValueError("Subscription plan is missing")
                while sub.next_invoice_date is not None and sub.next_invoice_date <= as_of:
                    if sub.expiry_date is not None and sub.next_invoice_date > sub.expiry_date:
                        break
                    period_start = sub.next_invoice_date
                    duplicate = db.scalar(
                        select(Invoice.id).where(
                            Invoice.subscription_id == sub.id,
                            Invoice.period_start == period_start,
                        )
                    )
                    if duplicate is not None:
                        sub.next_invoice_date = advance(period_start, plan.billing_period, sub.start_date)
                        skipped += 1
                        continue
                    try:
                        _make_invoice(db, sub, plan, as_of, period_start)
                        db.commit()
                        created += 1
                        sub = db.scalar(select(Subscription).where(Subscription.id == sub_id).with_for_update())
                    except IntegrityError:
                        db.rollback()
                        skipped += 1
                        sub = db.scalar(select(Subscription).where(Subscription.id == sub_id).with_for_update())
                        if sub is None or sub.next_invoice_date is None:
                            break
                        sub.next_invoice_date = advance(sub.next_invoice_date, plan.billing_period, sub.start_date)
                        db.commit()
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.exception("Invoice generation failed for subscription id %s", sub_id)
                failed.append({"sub_id": sub_id, "error": f"{type(exc).__name__}: invoice generation failed"})
    return GenerateResultOut(created=created, skipped_duplicates=skipped, failed=failed)


def get_invoice_breakdown(db: Session, actor: Actor, invoice_id: int) -> InvoiceBreakdownOut:
    query = select(Invoice).where(Invoice.id == invoice_id)
    if actor.role == "customer":
        query = query.where(Invoice.customer_id == actor.customer_id)
    invoice = db.scalar(query)
    if invoice is None:
        raise NotFoundError("Invoice not found")
    rows = list(db.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id).order_by(InvoiceLine.id)))
    lines = [
        InvoiceBreakdownLineOut(
            description=line.description, quantity=line.quantity, unit_price=line.unit_price,
            variant_extra=line.variant_extra, discount_name=line.discount_name,
            discount_amount=line.discount_amount, discount_reason=line.discount_reason,
            tax_name=line.tax_name, tax_rate_pct=line.tax_rate_pct,
            tax_amount=line.tax_amount, line_total=line.line_total,
        ) for line in rows
    ]
    return InvoiceBreakdownOut(
        invoice_id=invoice.id, invoice_number=invoice.number, lines=lines,
        subtotal=invoice.subtotal, discount_total=invoice.discount_total,
        tax_total=invoice.tax_total, total=invoice.total,
    )
