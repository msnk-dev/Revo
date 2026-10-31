from datetime import date, timedelta
from decimal import Decimal

from app.deps import Actor
from app.models import (
    Customer, Plan, Product, ProductVariantAttribute, ProductVariantValue,
    QuotationTemplate, QuotationTemplateLine, Subscription, SubscriptionStatusHistory,
)
from app.schemas.subscriptions import SubscriptionCreateIn, SubscriptionLineIn
from app.services import subscriptions
from app.errors import ForbiddenError, ValidationFailed


def setup_catalog(db_session):
    customer = Customer(name="Mina", email="mina@example.test", is_active=True)
    plan = Plan(name="Monthly", price=Decimal("1200.00"), billing_period="monthly", min_quantity=2,
                available_from=date.today() - timedelta(days=1), is_active=True)
    product = Product(name="Odoo", type="software", sales_price=Decimal("1000.00"), cost_price=Decimal("0.00"), is_active=True)
    db_session.add_all([customer, plan, product])
    db_session.flush()
    attr = ProductVariantAttribute(product_id=product.id, name="Edition")
    db_session.add(attr)
    db_session.flush()
    value = ProductVariantValue(attribute_id=attr.id, value="Premium", extra_price=Decimal("560.00"))
    db_session.add(value)
    db_session.commit()
    return customer, plan, product, value


def test_create_subscription_prices_first_line_and_records_history(db_session):
    customer, plan, product, variant = setup_catalog(db_session)
    actor = Actor(user_id=42, role="staff", customer_id=None)
    payload = SubscriptionCreateIn(
        customer_id=customer.id, plan_id=plan.id, start_date=date.today(),
        lines=[SubscriptionLineIn(product_id=product.id, quantity=2, variant_value_ids=[variant.id])],
    )
    sub = subscriptions.create_subscription(db_session, actor, payload)
    detail = subscriptions.as_detail(db_session, sub)
    assert sub.number.startswith("SUB-")
    assert detail["lines"][0]["unit_price"] == Decimal("1760.00")
    assert detail["lines"][0]["variant_value_ids"] == [variant.id]
    assert [(h.from_status, h.to_status) for h in db_session.query(SubscriptionStatusHistory).all()] == [(None, "draft")]


def test_number_generation_avoids_existing_seed_numbers(db_session):
    customer, plan, product, _variant = setup_catalog(db_session)
    seed = Subscription(number="SUB-000002", customer_id=customer.id, plan_id=plan.id,
                        status="active", start_date=date.today(), is_paused=False)
    db_session.add(seed)
    db_session.commit()
    actor = Actor(user_id=10, role="staff", customer_id=None)
    created = subscriptions.create_subscription(db_session, actor, SubscriptionCreateIn(
        customer_id=customer.id, plan_id=plan.id, start_date=date.today(),
        lines=[SubscriptionLineIn(product_id=product.id, quantity=2)],
    ))
    assert created.number == "SUB-000003"


def test_plan_minimum_is_per_line_and_invalid_variant_rejected(db_session):
    customer, plan, product, variant = setup_catalog(db_session)
    actor = Actor(user_id=1, role="staff", customer_id=None)
    too_small = SubscriptionCreateIn(customer_id=customer.id, plan_id=plan.id, start_date=date.today(),
        lines=[SubscriptionLineIn(product_id=product.id, quantity=1)])
    try:
        subscriptions.create_subscription(db_session, actor, too_small)
    except ValidationFailed as exc:
        assert "minimum quantity" in str(exc)
    else:
        raise AssertionError("line below plan minimum was accepted")
    wrong_variant = SubscriptionCreateIn(customer_id=customer.id, plan_id=plan.id, start_date=date.today(),
        lines=[SubscriptionLineIn(product_id=product.id, quantity=2, variant_value_ids=[variant.id + 99])])
    try:
        subscriptions.create_subscription(db_session, actor, wrong_variant)
    except ValidationFailed:
        pass
    else:
        raise AssertionError("unrelated variant was accepted")


def test_lifecycle_quotation_expiry_activation_and_pause(db_session):
    customer, plan, product, variant = setup_catalog(db_session)
    actor = Actor(user_id=5, role="staff", customer_id=None)
    sub = subscriptions.create_subscription(db_session, actor, SubscriptionCreateIn(
        customer_id=customer.id, plan_id=plan.id, start_date=date.today(),
        lines=[SubscriptionLineIn(product_id=product.id, quantity=2)],
    ))
    sub = subscriptions.transition(db_session, actor, sub.id, "quotation")
    sub.quotation_expires_on = date.today() - timedelta(days=1)
    db_session.commit()
    try:
        subscriptions.transition(db_session, actor, sub.id, "confirmed")
    except ValidationFailed:
        pass
    else:
        raise AssertionError("expired quotation was confirmed")
    sub.quotation_expires_on = date.today() + timedelta(days=1)
    db_session.commit()
    subscriptions.transition(db_session, actor, sub.id, "confirmed")
    sub = subscriptions.transition(db_session, actor, sub.id, "active")
    assert sub.next_invoice_date == sub.start_date
    assert subscriptions.pause(db_session, actor, sub.id).is_paused is True
    assert subscriptions.resume(db_session, actor, sub.id).is_paused is False
    assert [h.to_status for h in db_session.query(SubscriptionStatusHistory).order_by(SubscriptionStatusHistory.id)] == ["draft", "quotation", "confirmed", "active"]


def test_template_creation_sets_expiry_and_renewal_copies_lines(db_session):
    customer, plan, product, variant = setup_catalog(db_session)
    template = QuotationTemplate(name="Starter", plan_id=plan.id, validity_days=14)
    db_session.add(template)
    db_session.flush()
    db_session.add(QuotationTemplateLine(template_id=template.id, product_id=product.id, quantity=2))
    db_session.commit()
    actor = Actor(user_id=6, role="staff", customer_id=None)
    quote = subscriptions.create_from_template(db_session, actor, template.id, customer.id, date.today())
    assert quote.status == "quotation"
    assert quote.quotation_expires_on == date.today() + timedelta(days=14)
    quote.status = "active"
    quote.expiry_date = date.today() + timedelta(days=30)
    db_session.commit()
    renewal = subscriptions.renew(db_session, actor, quote.id)
    assert renewal.status == "draft"
    assert renewal.start_date == quote.expiry_date + timedelta(days=1)
    assert len(subscriptions.as_detail(db_session, renewal)["lines"]) == 1


def test_customer_scope_and_close_flags(db_session):
    customer, plan, product, _variant = setup_catalog(db_session)
    other = Customer(name="Other", email="other@example.test", is_active=True)
    db_session.add(other)
    db_session.commit()
    actor = Actor(user_id=99, role="customer", customer_id=customer.id)
    sub = subscriptions.create_subscription(db_session, Actor(user_id=5, role="staff", customer_id=None), SubscriptionCreateIn(
        customer_id=customer.id, plan_id=plan.id, start_date=date.today(), lines=[SubscriptionLineIn(product_id=product.id, quantity=2)]))
    assert subscriptions.get_subscription(db_session, actor, sub.id).id == sub.id
    try:
        subscriptions.create_subscription(db_session, actor, SubscriptionCreateIn(
            customer_id=other.id, plan_id=plan.id, start_date=date.today(), lines=[SubscriptionLineIn(product_id=product.id, quantity=2)]))
    except ForbiddenError:
        pass
    else:
        raise AssertionError("customer created a subscription for another customer")
    plan.closable = False
    db_session.commit()
    sub.status = "active"
    db_session.commit()
    try:
        subscriptions.close(db_session, actor, sub.id)
    except ForbiddenError:
        pass
    else:
        raise AssertionError("customer closed a non-closable plan")
