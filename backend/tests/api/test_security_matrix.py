from datetime import date
from decimal import Decimal

from app.models import Customer, Invoice, Plan, Product, Subscription


def login(client, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword1!"})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_discount_admin_write_and_staff_read(client, create_user, db_session):
    staff = create_user("discount-staff@example.com", "staff")
    admin = create_user("discount-admin@example.com", "admin")
    product = Product(name="Discount item", type="service", sales_price=Decimal("10.00"), cost_price=Decimal("0.00"), is_active=True)
    db_session.add(product)
    db_session.commit()
    payload = {"name": "10 percent", "type": "percent", "value": "10.00", "scope": "product",
               "product_ids": [product.id]}
    headers = login(client, staff.email)
    denied = client.post("/api/v1/discounts", json=payload, headers=headers)
    assert denied.status_code == 403
    assert client.get("/api/v1/discounts").status_code == 200
    headers = login(client, admin.email)
    created = client.post("/api/v1/discounts", json=payload, headers=headers)
    assert created.status_code == 201, created.text


def test_customer_cannot_open_reports_or_another_customers_invoice(client, create_user, db_session):
    owner_user = create_user("owner@example.com", "customer")
    other_user = create_user("other@example.com", "customer")
    owner = db_session.query(Customer).filter_by(user_id=owner_user.id).one()
    other = db_session.query(Customer).filter_by(user_id=other_user.id).one()
    plan = Plan(name="Security plan", price=Decimal("10.00"), billing_period="monthly", is_active=True)
    product = Product(name="Security product", type="service", sales_price=Decimal("10.00"), cost_price=Decimal("0.00"), is_active=True)
    db_session.add_all([plan, product])
    db_session.flush()
    sub = Subscription(number="SUB-SEC1", customer_id=other.id, plan_id=plan.id, status="active", start_date=date.today(), is_paused=False)
    db_session.add(sub)
    db_session.flush()
    invoice = Invoice(number="INV-SEC1", subscription_id=sub.id, customer_id=other.id, status="confirmed",
                      invoice_date=date.today(), due_date=date.today(), period_start=date.today(), period_end=date.today(),
                      subtotal=Decimal("10.00"), discount_total=Decimal("0.00"), tax_total=Decimal("0.00"),
                      total=Decimal("10.00"), amount_paid=Decimal("0.00"), amount_due=Decimal("10.00"))
    db_session.add(invoice)
    db_session.commit()
    login(client, owner_user.email)
    report = client.get("/api/v1/reports/summary?from=2026-01-01&to=2026-12-31")
    assert report.status_code == 403
    hidden = client.get(f"/api/v1/invoices/{invoice.id}")
    assert hidden.status_code == 404
    assert owner.id != other.id
