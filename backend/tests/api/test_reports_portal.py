from datetime import date
from decimal import Decimal

from app.deps import Actor
from app.models import Customer, Invoice, InvoiceLine, Payment, PaymentMethod, Plan, Product, Subscription, SubscriptionLine, Tax
from app.services import reports, customers, invoices
from app.errors import NotFoundError


def seed_revenue(db_session):
    customer = Customer(name="User", email="user@example.test", is_active=True)
    tax = Tax(name="No tax", rate_pct=Decimal("0.00"), is_active=True)
    plan = Plan(name="Monthly", price=Decimal("30.00"), billing_period="monthly", is_active=True)
    product = Product(name="Service", type="service", sales_price=Decimal("30.00"), cost_price=Decimal("0.00"), is_active=True)
    method = PaymentMethod(name="bank_transfer", is_active=True)
    db_session.add_all([customer, tax, plan, product, method])
    db_session.flush()
    sub = Subscription(number="SUB-R1", customer_id=customer.id, plan_id=plan.id, status="active", start_date=date(2026, 10, 1), next_invoice_date=date(2026, 11, 1), is_paused=False)
    db_session.add(sub)
    db_session.flush()
    db_session.add(SubscriptionLine(subscription_id=sub.id, product_id=product.id, description="Service", quantity=2, unit_price=Decimal("30.00"), tax_id=tax.id))
    invoice = Invoice(number="INV-R1", subscription_id=sub.id, customer_id=customer.id, status="confirmed",
                      invoice_date=date(2026, 10, 5), due_date=date(2026, 10, 10), period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
                      subtotal=Decimal("60.00"), discount_total=Decimal("0.00"), tax_total=Decimal("0.00"), total=Decimal("60.00"), amount_paid=Decimal("20.00"), amount_due=Decimal("40.00"))
    db_session.add(invoice)
    db_session.flush()
    db_session.add(InvoiceLine(invoice_id=invoice.id, product_id=product.id, description="Service", quantity=2, unit_price=Decimal("30.00"), variant_extra=Decimal("0.00"), discount_amount=Decimal("0.00"), tax_name="No tax", tax_rate_pct=Decimal("0.00"), tax_amount=Decimal("0.00"), line_total=Decimal("60.00")))
    db_session.add(Payment(invoice_id=invoice.id, method_id=method.id, amount=Decimal("20.00"), paid_on=date(2026, 10, 6)))
    db_session.commit()
    return customer, invoice


def test_reporting_mrr_revenue_outstanding_and_overdue(db_session):
    seed_revenue(db_session)
    summary = reports.get_summary(db_session, date(2026, 10, 1), date(2026, 10, 31))
    assert summary.active_subscriptions == 1
    assert summary.mrr == Decimal("60.00")
    assert summary.collected == Decimal("20.00")
    assert summary.invoiced == Decimal("60.00")
    assert summary.outstanding == Decimal("40.00")
    assert summary.overdue_count == 1
    monthly = reports.get_revenue_by_month(db_session, date(2026, 10, 1), date(2026, 11, 30))
    assert len(monthly) == 2
    assert monthly[0].revenue_collected == Decimal("20.00")
    assert monthly[1].invoiced == Decimal("0.00")
    assert reports.get_overdue_summary(db_session).amount_due == Decimal("40.00")


def test_customer_portal_helpers_are_scoped(db_session):
    customer, invoice = seed_revenue(db_session)
    actor = Actor(user_id=4, role="customer", customer_id=customer.id)
    assert invoices.list_for_customer(db_session, customer.id)[0].id == invoice.id
    assert len(customers.get_payment_history(db_session, customer.id)) == 1
    try:
        invoices.get_invoice(db_session, Actor(user_id=8, role="customer", customer_id=customer.id + 5), invoice.id)
    except NotFoundError:
        pass
    else:
        raise AssertionError("another customer was able to retrieve invoice")
