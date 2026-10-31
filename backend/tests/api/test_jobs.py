from datetime import date, timedelta
from decimal import Decimal

from app.models import Customer, Plan, Product, Subscription, SubscriptionStatusHistory
from app.jobs import tasks


def test_activation_and_auto_close_jobs_are_idempotent(db_session):
    customer = Customer(name="Job", email="job@example.test", is_active=True)
    plan = Plan(name="Auto close", price=Decimal("1.00"), billing_period="monthly", auto_close=True, is_active=True)
    product = Product(name="Item", type="service", sales_price=Decimal("1.00"), cost_price=Decimal("0.00"), is_active=True)
    db_session.add_all([customer, plan, product])
    db_session.flush()
    confirmed = Subscription(number="SUB-J1", customer_id=customer.id, plan_id=plan.id, status="confirmed", start_date=date(2026, 1, 1), is_paused=False)
    expired = Subscription(number="SUB-J2", customer_id=customer.id, plan_id=plan.id, status="active", start_date=date(2025, 1, 1), expiry_date=date(2026, 1, 1), is_paused=True)
    db_session.add_all([confirmed, expired])
    db_session.commit()
    assert tasks.activate_subscriptions(db_session, date(2026, 10, 1)) == 1
    assert confirmed.status == "active"
    assert confirmed.next_invoice_date == confirmed.start_date
    assert tasks.activate_subscriptions(db_session, date(2026, 10, 1)) == 0
    assert tasks.auto_close_expired(db_session, date(2026, 10, 1)) == 1
    assert expired.status == "closed"
    assert expired.is_paused is False
    assert tasks.auto_close_expired(db_session, date(2026, 10, 1)) == 0
    assert [(h.from_status, h.to_status) for h in db_session.query(SubscriptionStatusHistory).order_by(SubscriptionStatusHistory.id)] == [
        ("confirmed", "active"), ("active", "closed")
    ]


def test_expired_quotation_and_renewal_reminders(db_session):
    customer = Customer(name="Reminder", email="reminder@example.test", is_active=True)
    plan = Plan(name="Reminder plan", price=Decimal("1.00"), billing_period="monthly", is_active=True)
    db_session.add_all([customer, plan])
    db_session.flush()
    expired = Subscription(number="SUB-J3", customer_id=customer.id, plan_id=plan.id, status="quotation", start_date=date(2026, 1, 1), quotation_expires_on=date(2026, 2, 1), is_paused=False)
    soon = Subscription(number="SUB-J4", customer_id=customer.id, plan_id=plan.id, status="active", start_date=date(2026, 1, 1), expiry_date=date(2026, 10, 5), is_paused=False)
    db_session.add_all([expired, soon])
    db_session.commit()
    assert tasks.expired_quotations(db_session, date(2026, 3, 1)) == [expired.id]
    reminders = tasks.renewal_reminders(db_session, date(2026, 10, 1))
    assert [row["subscription_id"] for row in reminders] == [soon.id]
