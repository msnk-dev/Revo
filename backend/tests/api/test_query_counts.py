from datetime import date
from decimal import Decimal

from sqlalchemy import event

from app.deps import Actor
from app.models import (
    Customer, Discount, DiscountProduct, Plan, Product, QuotationTemplate,
    QuotationTemplateLine, Subscription, SubscriptionLine, Tax,
)
from app.services import catalog, discounts, subscriptions


def test_paginated_details_use_bounded_queries(db_session):
    customer = Customer(name="Queries", email="queries@example.test", is_active=True)
    plan = Plan(name="Queries", price=Decimal("1.00"), billing_period="monthly", is_active=True)
    product = Product(name="Queries", type="service", sales_price=Decimal("1.00"), cost_price=Decimal("0.00"), is_active=True)
    tax = Tax(name="Queries", rate_pct=Decimal("0.00"), is_active=True)
    db_session.add_all([customer, plan, product, tax])
    db_session.flush()
    templates = []
    discounts_rows = []
    for index in range(12):
        sub = Subscription(number=f"SUB-Q{index}", customer_id=customer.id, plan_id=plan.id, status="draft", start_date=date.today(), is_paused=False)
        template = QuotationTemplate(name=f"Template {index}", plan_id=plan.id, validity_days=10)
        discount = Discount(name=f"Discount {index}", type="fixed", value=Decimal("1.00"), scope="product", min_purchase=Decimal("0"), min_quantity=1, uses_count=0, is_active=True)
        db_session.add_all([sub, template, discount])
        db_session.flush()
        db_session.add_all([
            SubscriptionLine(subscription_id=sub.id, product_id=product.id, description="One", quantity=1, unit_price=Decimal("1.00"), tax_id=tax.id),
            QuotationTemplateLine(template_id=template.id, product_id=product.id, quantity=1),
            DiscountProduct(discount_id=discount.id, product_id=product.id),
        ])
        templates.append(template)
        discounts_rows.append(discount)
    db_session.commit()
    actor = Actor(user_id=7, role="staff", customer_id=None)
    query_count = [0]

    def count_query(*_args):
        query_count[0] += 1

    event.listen(db_session.get_bind(), "before_cursor_execute", count_query)
    try:
        rows, _total = subscriptions.list_subscriptions(db_session, actor, 1, 10, None)
        subscriptions.as_detail_list(db_session, rows)
        assert query_count[0] <= 5
        query_count[0] = 0
        catalog.list_quotation_templates(db_session, 1, 10, None)
        assert query_count[0] <= 4
        query_count[0] = 0
        discounts.list_discounts(db_session, 1, 10, None)
        assert query_count[0] <= 3
    finally:
        event.remove(db_session.get_bind(), "before_cursor_execute", count_query)
