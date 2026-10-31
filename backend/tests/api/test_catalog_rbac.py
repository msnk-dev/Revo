from decimal import Decimal

import pytest

from app.models import (
    PaymentMethod,
    Plan,
    Product,
    ProductVariantAttribute,
    ProductVariantValue,
    QuotationTemplate,
    QuotationTemplateLine,
    Tax,
)


def _login(client, email: str) -> None:
    result = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword1!"})
    assert result.status_code == 200


def _seed_catalog(db):
    tax = Tax(name="RBAC GST", rate_pct=Decimal("18.00"), is_active=True)
    db.add(tax)
    db.flush()
    product = Product(
        name="RBAC product",
        type="software",
        sales_price=Decimal("100.00"),
        cost_price=Decimal("0.00"),
        is_active=True,
    )
    plan = Plan(name="RBAC plan", price=Decimal("100.00"), billing_period="monthly", min_quantity=1, is_active=True)
    method = PaymentMethod(name="cash", is_active=True)
    db.add_all([product, plan, method])
    db.flush()
    attribute = ProductVariantAttribute(product_id=product.id, name="Brand")
    db.add(attribute)
    db.flush()
    variant = ProductVariantValue(attribute_id=attribute.id, value="Odoo", extra_price=Decimal("560.00"))
    template = QuotationTemplate(name="RBAC template", plan_id=plan.id, validity_days=30)
    db.add_all([variant, template])
    db.flush()
    db.add(QuotationTemplateLine(template_id=template.id, product_id=product.id, quantity=1))
    db.commit()
    return {"tax": tax.id, "product": product.id, "plan": plan.id, "method": method.id, "template": template.id}


@pytest.mark.parametrize(
    ("route_name", "method", "allowed", "success_status", "body"),
    [
        ("products_list", "GET", {"admin", "staff", "customer"}, 200, None),
        ("products_create", "POST", {"admin"}, 201, "product"),
        ("product_get", "GET", {"admin", "staff", "customer"}, 200, None),
        ("product_update", "PUT", {"admin"}, 200, "product"),
        ("product_delete", "DELETE", {"admin"}, 204, None),
        ("variants_list", "GET", {"admin", "staff", "customer"}, 200, None),
        ("variants_create", "POST", {"admin"}, 201, "variant"),
        ("taxes_list", "GET", {"admin", "staff"}, 200, None),
        ("taxes_create", "POST", {"admin"}, 201, "tax"),
        ("tax_get", "GET", {"admin", "staff"}, 200, None),
        ("tax_update", "PUT", {"admin"}, 200, "tax"),
        ("tax_delete", "DELETE", {"admin"}, 204, None),
        ("plans_list", "GET", {"admin", "staff", "customer"}, 200, None),
        ("plans_create", "POST", {"admin"}, 201, "plan"),
        ("plan_get", "GET", {"admin", "staff", "customer"}, 200, None),
        ("plan_update", "PUT", {"admin"}, 200, "plan"),
        ("plan_delete", "DELETE", {"admin"}, 204, None),
        ("methods_list", "GET", {"admin", "staff"}, 200, None),
        ("methods_create", "POST", {"admin"}, 201, "method"),
        ("method_update", "PUT", {"admin"}, 200, "method"),
        ("method_delete", "DELETE", {"admin"}, 204, None),
        ("templates_list", "GET", {"admin", "staff"}, 200, None),
        ("templates_create", "POST", {"admin"}, 201, "template"),
        ("template_get", "GET", {"admin", "staff"}, 200, None),
        ("template_update", "PUT", {"admin"}, 200, "template"),
        ("template_delete", "DELETE", {"admin"}, 204, None),
    ],
)
@pytest.mark.parametrize("role", ["admin", "staff", "customer", None])
def test_catalog_route_role_matrix(client, create_user, db_session, route_name, method, allowed, success_status, body, role):
    ids = _seed_catalog(db_session)
    if role is not None:
        user = create_user(f"{role}-{route_name}@example.com", role)
        _login(client, user.email)

    bodies = {
        "product": {"name": "Created product", "type": "software", "sales_price": "125.00"},
        "variant": {"name": "Edition", "values": [{"value": "Team", "extra_price": "10.00"}]},
        "tax": {"name": "Created GST", "rate_pct": "12.00"},
        "plan": {"name": "Created plan", "price": "200.00", "billing_period": "monthly", "min_quantity": 2},
        "method": {"name": "upi"},
        "template": {
            "name": "Created template",
            "plan_id": ids["plan"],
            "validity_days": 15,
            "lines": [{"product_id": ids["product"], "quantity": 2, "variant_value_ids": []}],
        },
    }
    paths = {
        "products_list": "/api/v1/products",
        "products_create": "/api/v1/products",
        "product_get": f"/api/v1/products/{ids['product']}",
        "product_update": f"/api/v1/products/{ids['product']}",
        "product_delete": f"/api/v1/products/{ids['product']}",
        "variants_list": f"/api/v1/products/{ids['product']}/variants",
        "variants_create": f"/api/v1/products/{ids['product']}/variants",
        "taxes_list": "/api/v1/taxes",
        "taxes_create": "/api/v1/taxes",
        "tax_get": f"/api/v1/taxes/{ids['tax']}",
        "tax_update": f"/api/v1/taxes/{ids['tax']}",
        "tax_delete": f"/api/v1/taxes/{ids['tax']}",
        "plans_list": "/api/v1/plans",
        "plans_create": "/api/v1/plans",
        "plan_get": f"/api/v1/plans/{ids['plan']}",
        "plan_update": f"/api/v1/plans/{ids['plan']}",
        "plan_delete": f"/api/v1/plans/{ids['plan']}",
        "methods_list": "/api/v1/payment-methods",
        "methods_create": "/api/v1/payment-methods",
        "method_update": f"/api/v1/payment-methods/{ids['method']}",
        "method_delete": f"/api/v1/payment-methods/{ids['method']}",
        "templates_list": "/api/v1/quotation-templates",
        "templates_create": "/api/v1/quotation-templates",
        "template_get": f"/api/v1/quotation-templates/{ids['template']}",
        "template_update": f"/api/v1/quotation-templates/{ids['template']}",
        "template_delete": f"/api/v1/quotation-templates/{ids['template']}",
    }
    csrf_token = client.cookies.get("csrf_token")
    headers = {"X-CSRF-Token": csrf_token} if method != "GET" and csrf_token else {}
    response = client.request(
        method,
        paths[route_name],
        headers=headers,
        json=bodies.get(body) if body else None,
    )
    expected = 401 if role is None else success_status if role in allowed else 403
    assert response.status_code == expected, (route_name, role, response.text)
