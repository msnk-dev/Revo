from datetime import date, timedelta
from decimal import Decimal

from app.deps import Actor
from app.models import (
    Customer, Discount, DiscountProduct, Invoice, InvoiceLine, PaymentMethod, Plan,
    Product, Subscription, SubscriptionLine, SubscriptionLineVariant, Tax,
    ProductVariantAttribute, ProductVariantValue,
)
from app.services import billing
from app.services import invoices, payments
from app.errors import ConflictError, NotFoundError
from app.schemas.invoices import PaymentCreateIn
from app.errors import ValidationFailed


def seed_active(db_session, *, cycle="monthly"):
    customer = Customer(name="Dev", email="dev@example.test", is_active=True)
    tax = Tax(name="VAT", rate_pct=Decimal("10.00"), is_active=True)
    plan = Plan(name="Plan", price=Decimal("10.00"), billing_period=cycle, min_quantity=1, is_active=True)
    product = Product(name="Software", type="software", sales_price=Decimal("10.00"), cost_price=Decimal("0.00"), default_tax_id=None, is_active=True)
    db_session.add_all([customer, tax, plan, product])
    db_session.flush()
    product.default_tax_id = tax.id
    sub = Subscription(number="SUB-000001", customer_id=customer.id, plan_id=plan.id, status="active",
                       start_date=date(2026, 1, 31), expiry_date=None, next_invoice_date=date(2026, 1, 31),
                       payment_terms_days=7, is_paused=False)
    db_session.add(sub)
    db_session.flush()
    db_session.add(SubscriptionLine(subscription_id=sub.id, product_id=product.id, description="Software", quantity=2,
                                    unit_price=Decimal("10.00"), tax_id=tax.id))
    db_session.commit()
    return customer, plan, product, sub, tax


def test_cadence_anchor_keeps_month_end_and_leap_year():
    assert billing.advance(date(2026, 1, 31), "monthly", date(2026, 1, 31)) == date(2026, 2, 28)
    assert billing.advance(date(2026, 2, 28), "monthly", date(2026, 1, 31)) == date(2026, 3, 31)
    assert billing.advance(date(2024, 2, 29), "yearly", date(2020, 2, 29)) == date(2025, 2, 28)


def test_generate_invoice_totals_and_idempotent_catchup(db_session):
    _customer, _plan, _product, sub, _tax = seed_active(db_session)
    first = billing.generate_due_invoices(db_session, date(2026, 3, 31))
    assert first.created == 3
    assert first.failed == []
    invoices = db_session.query(Invoice).order_by(Invoice.period_start).all()
    assert [invoice.period_start for invoice in invoices] == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
    assert invoices[0].period_end == date(2026, 2, 27)
    assert invoices[0].total == Decimal("22.00")
    assert sub.next_invoice_date == date(2026, 4, 30)
    second = billing.generate_due_invoices(db_session, date(2026, 3, 31))
    assert second.created == 0
    assert db_session.query(Invoice).count() == 3


def test_discount_uses_best_single_and_snapshot(db_session):
    customer, _plan, product, _sub, _tax = seed_active(db_session)
    percent = Discount(name="Ten", type="percent", value=Decimal("10.00"), scope="product", min_purchase=Decimal("0"),
                       min_quantity=1, uses_count=0, is_active=True)
    fixed = Discount(name="Fixed", type="fixed", value=Decimal("1.50"), scope="product", min_purchase=Decimal("0"),
                     min_quantity=1, uses_count=0, is_active=True)
    db_session.add_all([percent, fixed])
    db_session.flush()
    db_session.add_all([DiscountProduct(discount_id=percent.id, product_id=product.id), DiscountProduct(discount_id=fixed.id, product_id=product.id)])
    db_session.commit()
    assert billing.generate_due_invoices(db_session, date(2026, 1, 31)).created == 1
    line = db_session.query(InvoiceLine).one()
    assert line.discount_name == "Ten"
    assert line.discount_amount == Decimal("2.00")
    assert line.tax_amount == Decimal("1.80")
    assert line.line_total == Decimal("19.80")
    assert db_session.get(Discount, percent.id).uses_count == 1
    assert db_session.get(Discount, fixed.id).uses_count == 0


def test_breakdown_scopes_invoice_to_customer(db_session):
    customer, _plan, _product, _sub, _tax = seed_active(db_session)
    billing.generate_due_invoices(db_session, date(2026, 1, 31))
    invoice = db_session.query(Invoice).one()
    out = billing.get_invoice_breakdown(db_session, Actor(user_id=1, role="customer", customer_id=customer.id), invoice.id)
    assert out.total == Decimal("22.00")
    try:
        billing.get_invoice_breakdown(db_session, Actor(user_id=2, role="customer", customer_id=customer.id + 1), invoice.id)
    except NotFoundError:
        pass
    else:
        raise AssertionError("customer accessed another customer's invoice")


def test_payment_partial_then_paid_and_overpayment_rejected(db_session):
    _customer, _plan, _product, _sub, _tax = seed_active(db_session)
    billing.generate_due_invoices(db_session, date(2026, 1, 31))
    invoice = db_session.query(Invoice).one()
    invoices.confirm(db_session, invoice.id)
    method = PaymentMethod(name="cash", is_active=True)
    db_session.add(method)
    db_session.commit()
    payments.record_payment(db_session, invoice.id, PaymentCreateIn(method_id=method.id, amount=Decimal("10.00"), paid_on=date.today()), 1)
    assert db_session.get(Invoice, invoice.id).amount_due == Decimal("12.00")
    try:
        payments.record_payment(db_session, invoice.id, PaymentCreateIn(method_id=method.id, amount=Decimal("12.01"), paid_on=date.today()), 1)
    except ValidationFailed:
        pass
    else:
        raise AssertionError("overpayment was accepted")
    payments.record_payment(db_session, invoice.id, PaymentCreateIn(method_id=method.id, amount=Decimal("12.00"), paid_on=date.today()), 1)
    paid = db_session.get(Invoice, invoice.id)
    assert paid.status == "paid"
    assert paid.amount_due == Decimal("0.00")


def test_cancel_releases_discount_usage_once(db_session):
    _customer, _plan, product, _sub, _tax = seed_active(db_session)
    discount = Discount(name="A", type="fixed", value=Decimal("1.00"), scope="product", min_purchase=Decimal("0"), min_quantity=1, uses_count=0, is_active=True)
    db_session.add(discount)
    db_session.flush()
    db_session.add(DiscountProduct(discount_id=discount.id, product_id=product.id))
    db_session.commit()
    billing.generate_due_invoices(db_session, date(2026, 1, 31))
    assert db_session.get(Discount, discount.id).uses_count == 1
    invoice = db_session.query(Invoice).one()
    invoices.cancel(db_session, invoice.id)
    assert db_session.get(Discount, discount.id).uses_count == 0


def test_discount_usage_limit_is_global_and_fixed_amount_is_capped(db_session):
    customer, plan, product, first_sub, _tax = seed_active(db_session)
    second_sub = Subscription(number="SUB-SECOND", customer_id=customer.id, plan_id=plan.id, status="active",
                              start_date=date(2026, 1, 31), next_invoice_date=date(2026, 1, 31), is_paused=False)
    db_session.add(second_sub)
    db_session.flush()
    db_session.add(SubscriptionLine(subscription_id=second_sub.id, product_id=product.id, description="Second",
                                    quantity=2, unit_price=Decimal("10.00"), tax_id=None))
    discount = Discount(name="Limited", type="fixed", value=Decimal("99.00"), scope="product",
                        min_purchase=Decimal("0"), min_quantity=1, max_uses=1, uses_count=0, is_active=True)
    db_session.add(discount)
    db_session.flush()
    db_session.add(DiscountProduct(discount_id=discount.id, product_id=product.id))
    db_session.commit()
    result = billing.generate_due_invoices(db_session, date(2026, 1, 31))
    assert result.created == 2
    lines = db_session.query(InvoiceLine).order_by(InvoiceLine.id).all()
    assert lines[0].discount_name == "Limited"
    assert lines[0].discount_amount == Decimal("20.00")
    assert lines[1].discount_name is None
    assert db_session.get(Discount, discount.id).uses_count == 1


def test_pdf_generation_and_cannot_cancel_invoice_with_payment(db_session):
    customer, _plan, _product, _sub, _tax = seed_active(db_session)
    billing.generate_due_invoices(db_session, date(2026, 1, 31))
    invoice = db_session.query(Invoice).one()
    pdf = invoices.invoice_pdf(db_session, Actor(user_id=1, role="admin", customer_id=None), invoice.id)
    assert pdf.startswith(b"%PDF")
    invoices.confirm(db_session, invoice.id)
    method = PaymentMethod(name="card", is_active=True)
    db_session.add(method)
    db_session.commit()
    payments.record_payment(db_session, invoice.id, PaymentCreateIn(method_id=method.id, amount=Decimal("1.00"), paid_on=date.today()), 1)
    try:
        invoices.cancel(db_session, invoice.id)
    except ConflictError:
        pass
    else:
        raise AssertionError("invoice with payment was cancelled")
