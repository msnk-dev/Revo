from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.deps import Actor, require_roles, get_db
from app.schemas.contract import BreakdownOut, MonthRevenueOut, OverdueInvoiceOut, OverdueSummaryOut, SummaryOut
from app.schemas.invoices import PaymentReportOut
from app.services import reports

router = APIRouter(tags=["reports"])
DbSession = Annotated[Session, Depends(get_db)]
Reader = Annotated[Actor, Depends(require_roles("admin", "staff"))]


@router.get("/reports/summary", response_model=SummaryOut)
def summary(db: DbSession, actor: Reader, date_from: date = Query(alias="from"), date_to: date = Query(alias="to")) -> SummaryOut:
    return reports.get_summary(db, date_from, date_to)


@router.get("/reports/subscriptions", response_model=BreakdownOut)
def subscriptions_breakdown(db: DbSession, actor: Reader) -> BreakdownOut:
    return reports.get_active_subscriptions_breakdown(db)


@router.get("/reports/revenue", response_model=list[MonthRevenueOut])
def revenue(db: DbSession, actor: Reader, date_from: date = Query(alias="from"), date_to: date = Query(alias="to")) -> list[MonthRevenueOut]:
    return reports.get_revenue_by_month(db, date_from, date_to)


@router.get("/reports/overdue", response_model=list[OverdueInvoiceOut])
def overdue(db: DbSession, actor: Reader, limit: int = Query(default=50, ge=1, le=1000)) -> list[OverdueInvoiceOut]:
    return reports.list_overdue(db, limit)


@router.get("/reports/overdue/summary", response_model=OverdueSummaryOut)
def overdue_summary(db: DbSession, actor: Reader) -> OverdueSummaryOut:
    return reports.get_overdue_summary(db)


@router.get("/reports/payments", response_model=PaymentReportOut)
def payment_report(db: DbSession, actor: Reader, date_from: date = Query(alias="from"), date_to: date = Query(alias="to"),
                   page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100)) -> PaymentReportOut:
    items, total, amount = reports.get_payment_report(db, date_from, date_to, page, page_size)
    return PaymentReportOut(items=items, total=total, amount=amount, page=page, page_size=page_size)


@router.get("/reports/renewal-reminders")
def renewal_reminders(db: DbSession, actor: Reader):
    return reports.list_renewal_reminders(db)


@router.get("/reports/export.csv", response_class=Response)
def export_csv(db: DbSession, actor: Reader, date_from: date = Query(alias="from"), date_to: date = Query(alias="to")) -> Response:
    content = reports.export_report_csv(db, date_from, date_to)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="revo-report-{date_from.isoformat()}-{date_to.isoformat()}.csv"'},
    )
