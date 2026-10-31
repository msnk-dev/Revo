from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    PaymentMethod,
    Plan,
    Product,
    ProductVariantAttribute,
    ProductVariantValue,
    QuotationTemplate,
    QuotationTemplateLine,
    QuotationTemplateLineVariant,
    Tax,
)
from app.services.catalog import calculate_unit_price, plan_is_available


def _login(client, email: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword1!"})
    assert response.status_code == 200


def _csrf(client) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("csrf_token", "")}


def test_odoo_variant_adds_560_to_product_price(client, db_session, create_user):
    admin = create_user("catalog-admin@example.com", "admin")
    _login(client, admin.email)
    product_response = client.post(
        "/api/v1/products",
        headers=_csrf(client),
        json={"name": "Odoo Suite", "type": "software", "sales_price": "1200.00"},
    )
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]
    variant_response = client.post(
        f"/api/v1/products/{product_id}/variants",
        headers=_csrf(client),
        json={"name": "Brand", "values": [{"value": "Odoo", "extra_price": "560.00"}]},
    )
    assert variant_response.status_code == 201
    variant_id = variant_response.json()["values"][0]["id"]
    assert calculate_unit_price(db_session, product_id, [variant_id]) == Decimal("1760.00")


def test_customer_only_sees_active_products_and_plans(client, db_session, create_user):
    tax = Tax(name="GST", rate_pct=Decimal("18.00"), is_active=True)
    db_session.add(tax)
    db_session.flush()
    active_product = Product(
        name="Visible product", type="software", sales_price=Decimal("100.00"), cost_price=Decimal("0.00"), is_active=True
    )
    inactive_product = Product(
        name="Hidden product", type="software", sales_price=Decimal("100.00"), cost_price=Decimal("0.00"), is_active=False
    )
    active_plan = Plan(name="Visible plan", price=Decimal("100.00"), billing_period="monthly", min_quantity=1, is_active=True)
    inactive_plan = Plan(name="Hidden plan", price=Decimal("100.00"), billing_period="monthly", min_quantity=1, is_active=False)
    db_session.add_all([active_product, inactive_product, active_plan, inactive_plan])
    db_session.commit()
    user = create_user("customer-catalog@example.com", "customer")
    _login(client, user.email)

    products = client.get("/api/v1/products")
    plans = client.get("/api/v1/plans")
    hidden_product = client.get(f"/api/v1/products/{inactive_product.id}")
    hidden_plan = client.get(f"/api/v1/plans/{inactive_plan.id}")

    assert products.status_code == plans.status_code == 200
    assert [item["name"] for item in products.json()["items"]] == ["Visible product"]
    assert [item["name"] for item in plans.json()["items"]] == ["Visible plan"]
    assert hidden_product.status_code == hidden_plan.status_code == 404


def test_plan_availability_dates_are_inclusive():
    plan = Plan(
        name="Window",
        price=Decimal("1.00"),
        billing_period="monthly",
        min_quantity=1,
        available_from=date(2026, 1, 1),
        available_to=date(2026, 1, 31),
        is_active=True,
    )
    assert plan_is_available(plan, date(2026, 1, 1))
    assert plan_is_available(plan, date(2026, 1, 31))
    assert not plan_is_available(plan, date(2025, 12, 31))
    assert not plan_is_available(plan, date(2026, 2, 1))


@pytest.mark.parametrize(
    ("path", "body", "field"),
    [
        ("/api/v1/products", {"name": "Negative", "type": "software", "sales_price": "-1.00"}, "sales_price"),
        ("/api/v1/products", {"name": "Fraction", "type": "software", "sales_price": "1.001"}, "sales_price"),
        (
            "/api/v1/products",
            {"name": "Extra", "type": "software", "sales_price": "1.00", "unexpected": True},
            "unexpected",
        ),
        ("/api/v1/taxes", {"name": "Bad rate", "rate_pct": "100.01"}, "rate_pct"),
        ("/api/v1/taxes", {"name": "Fraction rate", "rate_pct": "1.001"}, "rate_pct"),
        (
            "/api/v1/plans",
            {"name": "Bad qty", "price": "1.00", "billing_period": "monthly", "min_quantity": 0},
            "min_quantity",
        ),
        (
            "/api/v1/plans",
            {
                "name": "Bad dates",
                "price": "1.00",
                "billing_period": "monthly",
                "available_from": "2026-02-01",
                "available_to": "2026-01-01",
            },
            "available_to",
        ),
        (
            "/api/v1/products/1/variants",
            {"name": "Brand", "values": [{"value": "Odoo", "extra_price": "560.001"}]},
            "extra_price",
        ),
        ("/api/v1/payment-methods", {"name": ""}, "name"),
        (
            "/api/v1/quotation-templates",
            {"name": "Empty", "plan_id": 1, "validity_days": 30, "lines": []},
            "lines",
        ),
        (
            "/api/v1/quotation-templates",
            {"name": "Bad quantity", "plan_id": 1, "validity_days": 30, "lines": [{"product_id": 1, "quantity": 0}]},
            "quantity",
        ),
    ],
)
def test_catalog_validation_returns_field_errors(client, create_user, path, body, field):
    admin = create_user(f"validation-{abs(hash(path + field))}@example.com", "admin")
    _login(client, admin.email)
    response = client.post(path, headers=_csrf(client), json=body)
    assert response.status_code == 422
    if field:
        assert any(field in key for key in response.json()["error"]["details"])


def test_template_copies_product_variant_references(client, create_user, db_session):
    tax = Tax(name="Template tax", rate_pct=Decimal("18.00"), is_active=True)
    db_session.add(tax)
    db_session.flush()
    product = Product(
        name="Template product", type="software", sales_price=Decimal("1200.00"), cost_price=Decimal("0.00"), is_active=True
    )
    plan = Plan(name="Template plan", price=Decimal("1200.00"), billing_period="monthly", min_quantity=1, is_active=True)
    db_session.add_all([product, plan])
    db_session.flush()
    attribute = ProductVariantAttribute(product_id=product.id, name="Brand")
    db_session.add(attribute)
    db_session.flush()
    variant = ProductVariantValue(attribute_id=attribute.id, value="Odoo", extra_price=Decimal("560.00"))
    db_session.add(variant)
    db_session.commit()
    admin = create_user("template-admin@example.com", "admin")
    _login(client, admin.email)

    response = client.post(
        "/api/v1/quotation-templates",
        headers=_csrf(client),
        json={
            "name": "Odoo template",
            "plan_id": plan.id,
            "validity_days": 30,
            "lines": [{"product_id": product.id, "quantity": 1, "variant_value_ids": [variant.id]}],
        },
    )

    assert response.status_code == 201
    template_id = response.json()["id"]
    stored_template = db_session.get(QuotationTemplate, template_id)
    stored_line = db_session.scalar(select(QuotationTemplateLine).where(QuotationTemplateLine.template_id == template_id))
    stored_variant_id = db_session.scalar(
        select(QuotationTemplateLineVariant.variant_value_id).where(
            QuotationTemplateLineVariant.line_id == stored_line.id
        )
    )
    assert stored_template.name == "Odoo template"
    assert stored_variant_id == variant.id

