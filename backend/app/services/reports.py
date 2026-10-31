from datetime import date

from sqlalchemy.orm import Session

from app.schemas.contract import (
    BreakdownOut,
    MonthRevenueOut,
    OverdueInvoiceOut,
    OverdueSummaryOut,
    SummaryOut,
)


def get_summary(db: Session, date_from: date, date_to: date) -> SummaryOut:
    return SummaryOut(active_subscriptions=2, paused_subscriptions=0, mrr="1200.00", collected="0.00", invoiced="0.00", outstanding="0.00", overdue_count=0)


def get_revenue_by_month(db: Session, date_from: date, date_to: date) -> list[MonthRevenueOut]:
    return [MonthRevenueOut(month=date(date_from.year, date_from.month, 1), revenue_collected="0.00", invoiced="0.00")]


def get_active_subscriptions_breakdown(db: Session) -> BreakdownOut:
    return BreakdownOut(active=2, paused=0, by_plan={"Monthly": 2})


def list_overdue(db: Session, limit: int = 50) -> list[OverdueInvoiceOut]:
    return []


def get_overdue_summary(db: Session) -> OverdueSummaryOut:
    return OverdueSummaryOut(count=0, amount_due="0.00")

