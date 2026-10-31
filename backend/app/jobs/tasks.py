from datetime import date, datetime, timedelta, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Plan, Subscription, SubscriptionStatusHistory
from app.services import billing

logger = logging.getLogger(__name__)


def activate_subscriptions(db: Session, today: date | None = None) -> int:
    current = today or date.today()
    rows = list(db.scalars(select(Subscription).where(
        Subscription.status == "confirmed", Subscription.start_date <= current
    ).order_by(Subscription.id).with_for_update(skip_locked=True)))
    for row in rows:
        row.status = "active"
        row.next_invoice_date = row.start_date
        db.add(SubscriptionStatusHistory(subscription_id=row.id, from_status="confirmed", to_status="active",
                                         changed_by=None, changed_at=datetime.now(timezone.utc)))
    db.commit()
    return len(rows)


def auto_close_expired(db: Session, today: date | None = None) -> int:
    current = today or date.today()
    rows = list(db.scalars(select(Subscription).join(Plan, Plan.id == Subscription.plan_id).where(
        Subscription.status == "active", Subscription.expiry_date < current, Plan.auto_close.is_(True)
    ).order_by(Subscription.id).with_for_update(skip_locked=True)))
    for row in rows:
        row.status = "closed"
        row.is_paused = False
        row.closed_at = datetime.now(timezone.utc)
        db.add(SubscriptionStatusHistory(subscription_id=row.id, from_status="active", to_status="closed",
                                         changed_by=None, changed_at=datetime.now(timezone.utc)))
    db.commit()
    return len(rows)


def expired_quotations(db: Session, today: date | None = None) -> list[int]:
    current = today or date.today()
    return list(db.scalars(select(Subscription.id).where(
        Subscription.status == "quotation", Subscription.quotation_expires_on.is_not(None),
        Subscription.quotation_expires_on < current,
    ).order_by(Subscription.id).limit(1000)))


def renewal_reminders(db: Session, today: date | None = None) -> list[dict]:
    current = today or date.today()
    expiry = current + timedelta(days=7)
    rows = db.scalars(select(Subscription).where(
        Subscription.status == "active", Subscription.expiry_date >= current,
        Subscription.expiry_date <= expiry,
    ).order_by(Subscription.expiry_date, Subscription.id).limit(100))
    return [{"subscription_id": row.id, "number": row.number, "customer_id": row.customer_id,
             "expiry_date": row.expiry_date} for row in rows]


def generate_invoices(as_of: date | None = None):
    current = as_of or date.today()
    with SessionLocal() as db:
        return billing.generate_due_invoices(db, current)


def activate_due() -> int:
    with SessionLocal() as db:
        return activate_subscriptions(db)


def auto_close_due() -> int:
    with SessionLocal() as db:
        return auto_close_expired(db)


def run_daily_brief() -> None:
    try:
        from app.ai.briefing import run_daily_brief as ai_run_daily_brief
    except ModuleNotFoundError as exc:
        if exc.name not in {"app.ai", "app.ai.briefing"}:
            raise
        logger.warning("Daily CFO brief skipped because Person B has not supplied app.ai.briefing.run_daily_brief")
        return
    with SessionLocal() as db:
        ai_run_daily_brief(db)


def log_expired_quotations() -> int:
    with SessionLocal() as db:
        return len(expired_quotations(db))


def log_renewal_reminders() -> int:
    with SessionLocal() as db:
        return len(renewal_reminders(db))
