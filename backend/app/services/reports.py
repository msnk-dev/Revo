from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import csv
from io import StringIO

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.errors import ValidationFailed
from app.models import Customer, Invoice, Payment, PaymentMethod, Plan, Subscription, SubscriptionLine
from app.schemas.invoices import PaymentReportRowOut
from app.schemas.contract import (
    BreakdownOut, MonthRevenueOut, OverdueInvoiceOut, OverdueSummaryOut, SummaryOut,
)

ZERO = Decimal("0.00")


def _round(value: Decimal | None) -> Decimal:
    return (value or ZERO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _valid_range(date_from: date, date_to: date) -> None:
    if date_to < date_from:
        raise ValidationFailed("Invalid report date range", {"to": "Must be on or after from"})


def get_summary(db: Session, date_from: date, date_to: date) -> SummaryOut:
    _valid_range(date_from, date_to)
    active_count = db.scalar(select(func.count()).select_from(Subscription).where(Subscription.status == "active", Subscription.is_paused.is_(False))) or 0
    paused_count = db.scalar(select(func.count()).select_from(Subscription).where(Subscription.status == "active", Subscription.is_paused.is_(True))) or 0
    mrr = ZERO
    period_totals = db.execute(
        select(Plan.billing_period, func.sum(SubscriptionLine.unit_price * SubscriptionLine.quantity))
        .join(Subscription, Subscription.plan_id == Plan.id)
        .join(SubscriptionLine, SubscriptionLine.subscription_id == Subscription.id)
        .where(Subscription.status == "active", Subscription.is_paused.is_(False))
        .group_by(Plan.billing_period)
    )
    factors = {"daily": Decimal(30), "weekly": Decimal(52) / Decimal(12), "monthly": Decimal(1), "yearly": Decimal(1) / Decimal(12)}
    for period, total in period_totals:
        mrr += Decimal(total or 0) * factors[period]
    collected = db.scalar(select(func.sum(Payment.amount)).where(Payment.paid_on >= date_from, Payment.paid_on <= date_to)) or ZERO
    invoiced = db.scalar(select(func.sum(Invoice.total)).where(
        Invoice.status.in_(("confirmed", "paid")), Invoice.invoice_date >= date_from, Invoice.invoice_date <= date_to
    )) or ZERO
    outstanding = db.scalar(select(func.sum(Invoice.amount_due)).where(Invoice.status == "confirmed")) or ZERO
    overdue_count, overdue_amount = _overdue_aggregate(db)
    return SummaryOut(active_subscriptions=active_count, paused_subscriptions=paused_count, mrr=_round(mrr),
                      collected=_round(Decimal(collected)), invoiced=_round(Decimal(invoiced)),
                      outstanding=_round(Decimal(outstanding)), overdue_count=overdue_count)


def get_revenue_by_month(db: Session, date_from: date, date_to: date) -> list[MonthRevenueOut]:
    _valid_range(date_from, date_to)
    first = date(date_from.year, date_from.month, 1)
    last = date(date_to.year, date_to.month, 1)
    payment_month = (extract("year", Payment.paid_on), extract("month", Payment.paid_on))
    invoice_month = (extract("year", Invoice.invoice_date), extract("month", Invoice.invoice_date))
    collected_by_month = {
        (int(year), int(month)): Decimal(total or 0)
        for year, month, total in db.execute(
            select(*payment_month, func.sum(Payment.amount))
            .where(Payment.paid_on >= date_from, Payment.paid_on <= date_to)
            .group_by(*payment_month)
        )
    }
    invoiced_by_month = {
        (int(year), int(month)): Decimal(total or 0)
        for year, month, total in db.execute(
            select(*invoice_month, func.sum(Invoice.total))
            .where(Invoice.status.in_(("confirmed", "paid")), Invoice.invoice_date >= date_from, Invoice.invoice_date <= date_to)
            .group_by(*invoice_month)
        )
    }
    rows = []
    month = first
    while month <= last:
        key = (month.year, month.month)
        rows.append(MonthRevenueOut(month=month, revenue_collected=_round(collected_by_month.get(key, ZERO)),
                                    invoiced=_round(invoiced_by_month.get(key, ZERO))))
        month = date(month.year + (month.month == 12), (month.month % 12) + 1, 1)
    return rows


def get_active_subscriptions_breakdown(db: Session) -> BreakdownOut:
    grouped = db.execute(
        select(Plan.name, func.count(Subscription.id))
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.status == "active", Subscription.is_paused.is_(False))
        .group_by(Plan.name)
    )
    by_plan = {name: count for name, count in grouped}
    active = db.scalar(select(func.count()).select_from(Subscription).where(Subscription.status == "active", Subscription.is_paused.is_(False))) or 0
    paused = db.scalar(select(func.count()).select_from(Subscription).where(Subscription.status == "active", Subscription.is_paused.is_(True))) or 0
    return BreakdownOut(active=active, paused=paused, by_plan=by_plan)


def list_overdue(db: Session, limit: int = 50) -> list[OverdueInvoiceOut]:
    today = date.today()
    rows = db.execute(
        select(Invoice, Customer.name).join(Customer, Customer.id == Invoice.customer_id)
        .where(Invoice.status == "confirmed", Invoice.amount_due > 0, Invoice.due_date < today)
        .order_by(Invoice.due_date, Invoice.id).limit(max(1, min(limit, 1000)))
    )
    return [OverdueInvoiceOut(invoice_id=invoice.id, invoice_number=invoice.number, customer_name=name,
                              due_date=invoice.due_date, days_overdue=(today - invoice.due_date).days,
                              amount_due=invoice.amount_due) for invoice, name in rows]


def _overdue_aggregate(db: Session) -> tuple[int, Decimal]:
    today = date.today()
    count, amount = db.execute(select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount_due), 0)).where(
        Invoice.status == "confirmed", Invoice.amount_due > 0, Invoice.due_date < today
    )).one()
    return count, Decimal(amount or 0)


def get_overdue_summary(db: Session) -> OverdueSummaryOut:
    count, amount = _overdue_aggregate(db)
    return OverdueSummaryOut(count=count, amount_due=_round(amount))


def get_payment_report(db: Session, date_from: date, date_to: date, page: int, page_size: int):
    _valid_range(date_from, date_to)
    filters = (Payment.paid_on >= date_from, Payment.paid_on <= date_to)
    query = (
        select(Payment, Invoice.number, Customer.name, PaymentMethod.name)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .join(Customer, Customer.id == Invoice.customer_id)
        .join(PaymentMethod, PaymentMethod.id == Payment.method_id)
        .where(*filters)
    )
    count = db.scalar(select(func.count()).select_from(Payment).where(*filters)) or 0
    amount = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(*filters)) or ZERO
    rows = db.execute(query.order_by(Payment.paid_on.desc(), Payment.id.desc()).offset((page - 1) * page_size).limit(page_size))
    items = [PaymentReportRowOut(id=p.id, invoice_id=p.invoice_id, invoice_number=number,
                                 customer_name=customer, amount=p.amount, paid_on=p.paid_on, method=method)
             for p, number, customer, method in rows]
    return items, count, _round(Decimal(amount))


def _spreadsheet_safe(value: object) -> str:
    text = "" if value is None else str(value)
    first = text.lstrip(" \t\r\n")[:1]
    return f"'{text}" if first in {"=", "+", "-", "@"} else text


def export_report_csv(db: Session, date_from: date, date_to: date) -> str:
    """Export the same date-filtered summary, revenue, and payment data as Reports."""
    _valid_range(date_from, date_to)
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(["section", "date", "invoice_number", "customer_name", "metric", "count", "amount"])

    summary = get_summary(db, date_from, date_to)
    for metric in ("active_subscriptions", "paused_subscriptions", "overdue_count"):
        writer.writerow(["summary", "", "", "", metric, getattr(summary, metric), ""])
    for metric in ("mrr", "collected", "invoiced", "outstanding"):
        writer.writerow(["summary", "", "", "", metric, "", getattr(summary, metric)])

    for point in get_revenue_by_month(db, date_from, date_to):
        writer.writerow(["revenue", point.month.isoformat(), "", "", "collected", "", point.revenue_collected])
        writer.writerow(["revenue", point.month.isoformat(), "", "", "invoiced", "", point.invoiced])

    breakdown = get_active_subscriptions_breakdown(db)
    writer.writerow(["subscriptions", "", "", "", "active", breakdown.active, ""])
    writer.writerow(["subscriptions", "", "", "", "paused", breakdown.paused, ""])
    for plan_name, count in sorted(breakdown.by_plan.items()):
        writer.writerow(["subscriptions", "", "", plan_name, "active_by_plan", count, ""])

    for item in list_overdue(db, limit=1000):
        writer.writerow(["overdue", item.due_date.isoformat(), item.invoice_number, item.customer_name,
                         "days_overdue", item.days_overdue, item.amount_due])

    page_size = 100
    items, total, _amount = get_payment_report(db, date_from, date_to, 1, page_size)
    page = 1
    while True:
        if page > 1:
            items, _total, _amount = get_payment_report(db, date_from, date_to, page, page_size)
        for item in items:
            writer.writerow(["payment", item.paid_on.isoformat(), item.invoice_number, item.customer_name,
                             item.method, "", item.amount])
        if page * page_size >= total:
            break
        page += 1

    # Sanitize every cell, including customer/plan-supplied text, before it reaches a spreadsheet.
    output.seek(0)
    safe_output = StringIO(newline="")
    safe_writer = csv.writer(safe_output, lineterminator="\r\n")
    for row in csv.reader(output):
        safe_writer.writerow([_spreadsheet_safe(cell) for cell in row])
    return safe_output.getvalue()


def list_renewal_reminders(db: Session, today: date | None = None) -> dict[str, object]:
    current = today or date.today()
    through = current + timedelta(days=7)
    filters = (
        Subscription.status == "active",
        Subscription.expiry_date >= current,
        Subscription.expiry_date <= through,
    )
    count = db.scalar(select(func.count()).select_from(Subscription).where(*filters)) or 0
    rows = db.execute(
        select(Subscription, Customer.name, Plan.name)
        .join(Customer, Customer.id == Subscription.customer_id)
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(*filters)
        .order_by(Subscription.expiry_date, Subscription.id)
        .limit(100)
    )
    items = [
        {
            "subscription_id": subscription.id,
            "number": subscription.number,
            "customer_name": customer_name,
            "plan_name": plan_name,
            "expiry_date": subscription.expiry_date,
            "days_remaining": (subscription.expiry_date - current).days,
        }
        for subscription, customer_name, plan_name in rows
    ]
    return {"count": count, "items": items}
